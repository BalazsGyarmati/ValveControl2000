import paho.mqtt.client as mqtt
import ssl
import logging
from typing import Optional, Callable, Dict, Any
from threading import Lock

class MQTTClient:
    """MQTT client for handling valve control communication"""

    def __init__(self, config: Dict[str, Any],
                _,
                ngettext,
                on_zone_state_change: Optional[Callable[[int, bool], None]] = None,
                on_connection_change: Optional[Callable[[bool], None]] = None):
        self.config = config
        self.client = mqtt.Client(client_id=config['client_id'])
        self.connected = False
        self.connection_lock = Lock()
        self.on_zone_state_change = on_zone_state_change
        self.on_connection_change = on_connection_change
        self.logger = logging.getLogger(__name__)
        self._ = _
        self.ngettext = ngettext

        # Disable automatic reconnect
        self.client.reconnect_delay_set(120, 120)  # Set high reconnect delay
        self.client.loop_stop()  # Ensure loop is stopped

        # Set up callbacks
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message

        # Configure authentication if provided
        if config['username'] and config['password']:
            self.client.username_pw_set(config['username'], config['password'])

        # Configure TLS if enabled
        if config['use_tls']:
            if config['ca_cert_path']:
                self.client.tls_set(
                    ca_certs=config['ca_cert_path'],
                    cert_reqs=ssl.CERT_REQUIRED,
                    tls_version=ssl.PROTOCOL_TLS
                )
            else:
                self.client.tls_set(cert_reqs=ssl.CERT_NONE)

    def connect(self) -> bool:
        """
        Connect to MQTT broker

        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            with self.connection_lock:
                if not self.connected:
                    # Set reconnect flag to False
                    self.client._clean_session = True
                    self.client._connect_handler = None

                    self.client.connect(
                        self.config['broker'],
                        self.config['port'],
                        keepalive=60
                    )
                    self.client.loop_start()
                    return True
            return False
        except Exception as e:
            self.logger.error(self._("Failed to connect to MQTT broker: {}").format(e))
            if self.on_connection_change:
                self.on_connection_change(False)
            return False

    def disconnect(self) -> None:
        """Disconnect from MQTT broker"""
        try:
            with self.connection_lock:
                if self.connected:
                    self.client.loop_stop()
                    self.client.disconnect()
        except Exception as e:
            self.logger.error(self._("Error disconnecting from MQTT broker: {}").format(e))

    def publish_zone_command(self, zone_id: int, state: bool) -> None:
        """
        Publish zone command

        Args:
            zone_id: ID of the zone
            state: True for on, False for off
        """
        if not self.connected:
            self.logger.warning(self._("Cannot publish: Not connected to MQTT broker"))
            return

        topic = f"{self.config['topic_prefix']}/zone/{zone_id}/command"
        payload = "on" if state else "off"

        try:
            self.client.publish(topic, payload, qos=1, retain=False)
        except Exception as e:
            self.logger.error(self._("Failed to publish zone command: {}").format(e))

    def _on_connect(self, client, userdata, flags, rc):
        """Handle connection established event"""
        if rc == 0:
            self.connected = True
            self.logger.info(self._("Connected to MQTT broker"))
            if self.on_connection_change:
                self.on_connection_change(True)

            # Subscribe to state topics for all possible zones
            for zone_id in range(8):
                topic = f"{self.config['topic_prefix']}/zone/{zone_id}/state"
                self.client.subscribe(topic, qos=1)
        else:
            self.logger.error(self._("Failed to connect to MQTT broker with code: {}").format(rc))
            if self.on_connection_change:
                self.on_connection_change(False)

    def _on_disconnect(self, client, userdata, rc):
        """Handle disconnection event"""
        self.connected = False
        self.logger.warning(self._("Disconnected from MQTT broker"))
        if self.on_connection_change:
            self.on_connection_change(False)

    def _on_message(self, client, userdata, message):
        """Handle incoming messages"""
        try:
            # Parse topic to extract zone ID
            # Expected format: {prefix}/zone/{zone_id}/state
            parts = message.topic.split('/')
            if len(parts) != 4 or parts[1] != 'zone' or parts[3] != 'state':
                return

            try:
                zone_id = int(parts[2])
            except ValueError:
                self.logger.error(self._("Invalid zone ID in topic: {}").format(message.topic))
                return

            # Parse payload
            payload = message.payload.decode().lower()
            if payload not in ['on', 'off']:
                self.logger.error(self._("Invalid state payload: {}").format(payload))
                return

            if self.on_zone_state_change:
                is_on = payload == 'on'
                self.on_zone_state_change(zone_id, is_on)

        except Exception as e:
            self.logger.error(self._("Error processing MQTT message: {}").format(e))

    def __del__(self):
        """Ensure proper cleanup on deletion"""
        self.disconnect()
        self.client.loop_stop()
