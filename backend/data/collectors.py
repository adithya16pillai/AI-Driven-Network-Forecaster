import asyncio
import logging
import psutil
import subprocess
import time
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import socket
import struct
import platform
import netifaces
import concurrent.futures
from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..models import NetworkMetric, Device
from ..config import settings

logger = logging.getLogger(__name__)

@dataclass
class NetworkDevice:
    """Represents a network device"""
    device_id: str
    ip_address: str
    device_type: str = "unknown"
    location: str = "unknown"
    status: str = "unknown"

@dataclass
class MetricData:
    """Represents collected metric data"""
    device_id: str
    metric_name: str
    value: float
    unit: str
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None

class BaseCollector:
    """Base class for all metric collectors"""
    
    def __init__(self, collection_interval: int = 60):
        self.collection_interval = collection_interval
        self.is_running = False
        self._stop_event = asyncio.Event()
        
    async def start(self):
        """Start the collector"""
        self.is_running = True
        self._stop_event.clear()
        logger.info(f"Starting {self.__class__.__name__}")
        
        while not self._stop_event.is_set():
            try:
                await self.collect()
                await asyncio.sleep(self.collection_interval)
            except Exception as e:
                logger.error(f"Error in {self.__class__.__name__}: {e}")
                await asyncio.sleep(5)  # Wait before retrying
                
    async def stop(self):
        """Stop the collector"""
        self.is_running = False
        self._stop_event.set()
        logger.info(f"Stopping {self.__class__.__name__}")
        
    async def collect(self):
        """Override this method to implement collection logic"""
        raise NotImplementedError

class SystemMetricsCollector(BaseCollector):
    """Collects system-level network metrics"""
    
    def __init__(self, device_id: str = None, **kwargs):
        super().__init__(**kwargs)
        self.device_id = device_id or socket.gethostname()
        
    async def collect(self):
        """Collect system network metrics"""
        try:
            metrics = []
            timestamp = datetime.utcnow()
            
            # Network I/O metrics
            net_io = psutil.net_io_counters()
            if net_io:
                metrics.extend([
                    MetricData(
                        device_id=self.device_id,
                        metric_name="bytes_sent",
                        value=float(net_io.bytes_sent),
                        unit="bytes",
                        timestamp=timestamp
                    ),
                    MetricData(
                        device_id=self.device_id,
                        metric_name="bytes_recv",
                        value=float(net_io.bytes_recv),
                        unit="bytes",
                        timestamp=timestamp
                    ),
                    MetricData(
                        device_id=self.device_id,
                        metric_name="packets_sent",
                        value=float(net_io.packets_sent),
                        unit="packets",
                        timestamp=timestamp
                    ),
                    MetricData(
                        device_id=self.device_id,
                        metric_name="packets_recv",
                        value=float(net_io.packets_recv),
                        unit="packets",
                        timestamp=timestamp
                    ),
                ])
                
                if hasattr(net_io, 'dropin') and net_io.dropin is not None:
                    metrics.append(MetricData(
                        device_id=self.device_id,
                        metric_name="packet_loss",
                        value=float(net_io.dropin + net_io.dropout),
                        unit="packets",
                        timestamp=timestamp
                    ))
            
            # CPU and Memory metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            
            metrics.extend([
                MetricData(
                    device_id=self.device_id,
                    metric_name="cpu_usage",
                    value=float(cpu_percent),
                    unit="%",
                    timestamp=timestamp
                ),
                MetricData(
                    device_id=self.device_id,
                    metric_name="memory_usage",
                    value=float(memory.percent),
                    unit="%",
                    timestamp=timestamp
                ),
            ])
            
            # Network connections
            connections = len(psutil.net_connections())
            metrics.append(MetricData(
                device_id=self.device_id,
                metric_name="active_connections",
                value=float(connections),
                unit="connections",
                timestamp=timestamp
            ))
            
            await self._store_metrics(metrics)
            
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
    
    async def _store_metrics(self, metrics: List[MetricData]):
        """Store metrics in database"""
        db = SessionLocal()
        try:
            for metric in metrics:
                db_metric = NetworkMetric(
                    device_id=metric.device_id,
                    metric_name=metric.metric_name,
                    value=metric.value,
                    unit=metric.unit,
                    timestamp=metric.timestamp,
                    metadata=metric.metadata
                )
                db.add(db_metric)
            db.commit()
            logger.debug(f"Stored {len(metrics)} metrics")
        except Exception as e:
            logger.error(f"Error storing metrics: {e}")
            db.rollback()
        finally:
            db.close()

class PingCollector(BaseCollector):
    """Collects latency metrics using ping"""
    
    def __init__(self, targets: List[str] = None, **kwargs):
        super().__init__(**kwargs)
        self.targets = targets or ["8.8.8.8", "1.1.1.1"]  # Default DNS servers
        self.device_id = socket.gethostname()
        
    async def collect(self):
        """Collect ping latency metrics"""
        try:
            tasks = [self._ping_target(target) for target in self.targets]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            metrics = []
            timestamp = datetime.utcnow()
            
            for target, result in zip(self.targets, results):
                if isinstance(result, Exception):
                    logger.warning(f"Ping to {target} failed: {result}")
                    continue
                    
                if result is not None:
                    metrics.append(MetricData(
                        device_id=self.device_id,
                        metric_name="latency",
                        value=float(result),
                        unit="ms",
                        timestamp=timestamp,
                        metadata={"target": target}
                    ))
            
            await self._store_metrics(metrics)
            
        except Exception as e:
            logger.error(f"Error collecting ping metrics: {e}")
    
    async def _ping_target(self, target: str) -> Optional[float]:
        """Ping a single target and return latency"""
        try:
            if platform.system().lower() == "windows":
                cmd = ["ping", "-n", "1", target]
            else:
                cmd = ["ping", "-c", "1", target]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                output = stdout.decode()
                # Parse ping output to extract latency
                if platform.system().lower() == "windows":
                    # Windows: "time=1ms" or "time<1ms"
                    import re
                    match = re.search(r'time[=<](\d+(?:\.\d+)?)ms', output)
                    if match:
                        return float(match.group(1))
                else:
                    # Linux/Mac: "time=1.234 ms"
                    import re
                    match = re.search(r'time=(\d+(?:\.\d+)?)\s*ms', output)
                    if match:
                        return float(match.group(1))
            
            return None
            
        except Exception as e:
            logger.warning(f"Error pinging {target}: {e}")
            return None
    
    async def _store_metrics(self, metrics: List[MetricData]):
        """Store metrics in database"""
        db = SessionLocal()
        try:
            for metric in metrics:
                db_metric = NetworkMetric(
                    device_id=metric.device_id,
                    metric_name=metric.metric_name,
                    value=metric.value,
                    unit=metric.unit,
                    timestamp=metric.timestamp,
                    metadata=metric.metadata
                )
                db.add(db_metric)
            db.commit()
        except Exception as e:
            logger.error(f"Error storing ping metrics: {e}")
            db.rollback()
        finally:
            db.close()

class BandwidthCollector(BaseCollector):
    """Collects bandwidth utilization metrics"""
    
    def __init__(self, interface: str = None, **kwargs):
        super().__init__(**kwargs)
        self.interface = interface
        self.device_id = socket.gethostname()
        self.previous_stats = {}
        
    async def collect(self):
        """Collect bandwidth metrics"""
        try:
            interfaces = self._get_interfaces()
            metrics = []
            timestamp = datetime.utcnow()
            
            for interface_name, stats in interfaces.items():
                if self.interface and interface_name != self.interface:
                    continue
                    
                # Calculate bandwidth if we have previous stats
                if interface_name in self.previous_stats:
                    prev_stats = self.previous_stats[interface_name]
                    time_delta = self.collection_interval
                    
                    bytes_sent_rate = (stats['bytes_sent'] - prev_stats['bytes_sent']) / time_delta
                    bytes_recv_rate = (stats['bytes_recv'] - prev_stats['bytes_recv']) / time_delta
                    
                    # Convert to Mbps
                    sent_mbps = (bytes_sent_rate * 8) / (1024 * 1024)
                    recv_mbps = (bytes_recv_rate * 8) / (1024 * 1024)
                    
                    metrics.extend([
                        MetricData(
                            device_id=self.device_id,
                            metric_name="bandwidth_out",
                            value=float(sent_mbps),
                            unit="Mbps",
                            timestamp=timestamp,
                            metadata={"interface": interface_name}
                        ),
                        MetricData(
                            device_id=self.device_id,
                            metric_name="bandwidth_in",
                            value=float(recv_mbps),
                            unit="Mbps",
                            timestamp=timestamp,
                            metadata={"interface": interface_name}
                        ),
                        MetricData(
                            device_id=self.device_id,
                            metric_name="bandwidth_total",
                            value=float(sent_mbps + recv_mbps),
                            unit="Mbps",
                            timestamp=timestamp,
                            metadata={"interface": interface_name}
                        ),
                    ])
                
                self.previous_stats[interface_name] = stats
            
            await self._store_metrics(metrics)
            
        except Exception as e:
            logger.error(f"Error collecting bandwidth metrics: {e}")
    
    def _get_interfaces(self) -> Dict[str, Dict[str, int]]:
        """Get network interface statistics"""
        interfaces = {}
        
        try:
            # Use psutil to get per-interface stats
            stats = psutil.net_io_counters(pernic=True)
            
            for interface_name, interface_stats in stats.items():
                # Skip loopback and virtual interfaces
                if interface_name.startswith(('lo', 'docker', 'veth')):
                    continue
                    
                interfaces[interface_name] = {
                    'bytes_sent': interface_stats.bytes_sent,
                    'bytes_recv': interface_stats.bytes_recv,
                    'packets_sent': interface_stats.packets_sent,
                    'packets_recv': interface_stats.packets_recv,
                }
                
        except Exception as e:
            logger.error(f"Error getting interface stats: {e}")
            
        return interfaces
    
    async def _store_metrics(self, metrics: List[MetricData]):
        """Store metrics in database"""
        db = SessionLocal()
        try:
            for metric in metrics:
                db_metric = NetworkMetric(
                    device_id=metric.device_id,
                    metric_name=metric.metric_name,
                    value=metric.value,
                    unit=metric.unit,
                    timestamp=metric.timestamp,
                    metadata=metric.metadata
                )
                db.add(db_metric)
            db.commit()
        except Exception as e:
            logger.error(f"Error storing bandwidth metrics: {e}")
            db.rollback()
        finally:
            db.close()

class NetworkDiscoveryCollector(BaseCollector):
    """Discovers and monitors network devices"""
    
    def __init__(self, subnet: str = None, **kwargs):
        super().__init__(**kwargs)
        self.subnet = subnet or self._get_local_subnet()
        self.device_id = socket.gethostname()
        
    async def collect(self):
        """Discover network devices"""
        try:
            devices = await self._discover_devices()
            await self._update_device_registry(devices)
            
        except Exception as e:
            logger.error(f"Error in network discovery: {e}")
    
    def _get_local_subnet(self) -> str:
        """Get the local subnet for discovery"""
        try:
            # Get default gateway interface
            gateways = netifaces.gateways()
            default_interface = gateways['default'][netifaces.AF_INET][1]
            
            # Get IP and netmask of default interface
            addrs = netifaces.ifaddresses(default_interface)
            ip_info = addrs[netifaces.AF_INET][0]
            
            import ipaddress
            network = ipaddress.IPv4Network(f"{ip_info['addr']}/{ip_info['netmask']}", strict=False)
            return str(network.network_address) + "/" + str(network.prefixlen)
            
        except Exception:
            return "192.168.1.0/24"  # Default fallback
    
    async def _discover_devices(self) -> List[NetworkDevice]:
        """Discover devices on the network"""
        devices = []
        
        try:
            import ipaddress
            network = ipaddress.IPv4Network(self.subnet, strict=False)
            
            # Limit to reasonable subnet sizes
            if network.num_addresses > 256:
                logger.warning(f"Subnet {self.subnet} too large, limiting discovery")
                return devices
            
            # Create ping tasks for all IPs in subnet
            tasks = []
            for ip in network.hosts():
                tasks.append(self._check_device(str(ip)))
            
            # Run with limited concurrency
            semaphore = asyncio.Semaphore(20)  # Limit concurrent pings
            
            async def sem_ping(ip_task):
                async with semaphore:
                    return await ip_task
            
            results = await asyncio.gather(*[sem_ping(task) for task in tasks], return_exceptions=True)
            
            for result in results:
                if isinstance(result, NetworkDevice):
                    devices.append(result)
                    
        except Exception as e:
            logger.error(f"Error discovering devices: {e}")
            
        return devices
    
    async def _check_device(self, ip: str) -> Optional[NetworkDevice]:
        """Check if a device is reachable and gather info"""
        try:
            # Simple ping check
            if platform.system().lower() == "windows":
                cmd = ["ping", "-n", "1", "-w", "1000", ip]
            else:
                cmd = ["ping", "-c", "1", "-W", "1", ip]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            await process.communicate()
            
            if process.returncode == 0:
                # Device is reachable, try to get more info
                device_type = await self._identify_device_type(ip)
                
                return NetworkDevice(
                    device_id=f"device_{ip.replace('.', '_')}",
                    ip_address=ip,
                    device_type=device_type,
                    status="online"
                )
            
            return None
            
        except Exception:
            return None
    
    async def _identify_device_type(self, ip: str) -> str:
        """Try to identify device type based on open ports"""
        common_ports = {
            22: "server",     # SSH
            23: "router",     # Telnet
            80: "server",     # HTTP
            161: "router",    # SNMP
            443: "server",    # HTTPS
            8080: "server",   # HTTP Alt
        }
        
        try:
            for port, device_type in common_ports.items():
                if await self._check_port(ip, port):
                    return device_type
        except Exception:
            pass
            
        return "unknown"
    
    async def _check_port(self, ip: str, port: int, timeout: float = 1.0) -> bool:
        """Check if a port is open"""
        try:
            future = asyncio.open_connection(ip, port)
            reader, writer = await asyncio.wait_for(future, timeout=timeout)
            writer.close()
            await writer.wait_closed()
            return True
        except Exception:
            return False
    
    async def _update_device_registry(self, devices: List[NetworkDevice]):
        """Update device registry in database"""
        db = SessionLocal()
        try:
            for device in devices:
                # Check if device already exists
                existing = db.query(Device).filter(Device.device_id == device.device_id).first()
                
                if existing:
                    # Update existing device
                    existing.status = device.status
                    existing.last_seen = datetime.utcnow()
                else:
                    # Create new device
                    db_device = Device(
                        device_id=device.device_id,
                        device_type=device.device_type,
                        ip_address=device.ip_address,
                        location=device.location,
                        status=device.status,
                        last_seen=datetime.utcnow()
                    )
                    db.add(db_device)
            
            db.commit()
            logger.info(f"Updated {len(devices)} devices in registry")
            
        except Exception as e:
            logger.error(f"Error updating device registry: {e}")
            db.rollback()
        finally:
            db.close()

class MetricsCollectionManager:
    """Manages all metric collectors"""
    
    def __init__(self):
        self.collectors: List[BaseCollector] = []
        self.running = False
        
    def add_collector(self, collector: BaseCollector):
        """Add a collector to the manager"""
        self.collectors.append(collector)
        logger.info(f"Added collector: {collector.__class__.__name__}")
    
    async def start_all(self):
        """Start all collectors"""
        if self.running:
            logger.warning("Collection manager already running")
            return
            
        self.running = True
        logger.info("Starting all collectors")
        
        tasks = [collector.start() for collector in self.collectors]
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def stop_all(self):
        """Stop all collectors"""
        if not self.running:
            return
            
        self.running = False
        logger.info("Stopping all collectors")
        
        for collector in self.collectors:
            await collector.stop()
    
    def get_default_collectors(self) -> List[BaseCollector]:
        """Get default set of collectors"""
        return [
            SystemMetricsCollector(collection_interval=30),
            PingCollector(collection_interval=60),
            BandwidthCollector(collection_interval=30),
            NetworkDiscoveryCollector(collection_interval=300),  # Every 5 minutes
        ]

# Global manager instance
metrics_manager = MetricsCollectionManager()

async def start_collection():
    """Start metric collection with default collectors"""
    try:
        # Add default collectors
        for collector in metrics_manager.get_default_collectors():
            metrics_manager.add_collector(collector)
        
        # Start collection
        await metrics_manager.start_all()
        
    except Exception as e:
        logger.error(f"Error starting metric collection: {e}")

async def stop_collection():
    """Stop metric collection"""
    try:
        await metrics_manager.stop_all()
    except Exception as e:
        logger.error(f"Error stopping metric collection: {e}")