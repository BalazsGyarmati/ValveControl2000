from tkinter import ttk, StringVar, BooleanVar, BOTH, X, filedialog
import tkinter as tk
import os
from typing import Any
from mqtt_client import MQTTClient

class ZoneControlFrame(ttk.Frame):
    def __init__(self, parent, config, _, ngettext):
        super().__init__(parent)
        self.config = config
        self._ = _
        self.ngettext = ngettext
        self.active_zones = {}
        self.mqtt_client = None

        # Initialize status variables first
        self.mqtt_status_var = StringVar(value="●")
        self.mqtt_status_text_var = StringVar(value=self._("Disconnected"))

        # Create notebook for tabs
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=BOTH, expand=True)

        # Create Control and Configuration tabs
        self.control_frame = ttk.Frame(self.notebook)
        self.config_frame = ttk.Frame(self.notebook)

        self.notebook.add(self.control_frame, text=self._("Control"))
        self.notebook.add(self.config_frame, text=self._("Configuration"))

        self.setup_control_panel()
        self.setup_config_panel()


    def init_mqtt(self):
        """Initialize MQTT client with current configuration"""
        if self.mqtt_client:
            self.mqtt_client.disconnect()

        self.mqtt_client = MQTTClient(
            self.config.zone_config.mqtt,
            _ = self._,
            ngettext = self.ngettext,
            on_zone_state_change=self.handle_mqtt_state_change,
            on_connection_change=self.update_mqtt_status
        )
        if self.config.zone_config.mqtt.get('enabled', False):
            self.mqtt_client.connect()

    def setup_control_panel(self):
        control_frame = ttk.Frame(self.control_frame)
        control_frame.pack(fill=BOTH, expand=True, padx=20, pady=20)

        style = ttk.Style()
        style.configure('Large.TButton', padding=(20, 10), font=('TkDefaultFont', 14, 'bold'))
        style.configure('ZoneName.TLabel', font=('TkDefaultFont', 16, 'bold'), padding=(0, 5))
        style.configure('MasterInfo.TLabel', font=('TkDefaultFont', 14), foreground='#666666', padding=(0, 5))
        style.configure('Status.TLabel', font=('TkDefaultFont', 32))

        for i in range(2):
            control_frame.grid_columnconfigure(i, weight=1, pad=20)

        for i, zone in enumerate(self.config.zone_config.zones):
            col = i % 2
            row_base = (i // 2) * 2  # Each zone takes 2 rows now

            # Top frame for name and status
            top_frame = ttk.Frame(control_frame)
            top_frame.grid(row=row_base, column=col, padx=10, pady=(10, 5))

            # Name and master info
            name_frame = ttk.Frame(top_frame)
            name_frame.pack(side=tk.LEFT)

            name_label = ttk.Label(name_frame, text=zone['name'], style='ZoneName.TLabel')
            name_label.pack(anchor=tk.W)

            master_text = ""
            if zone['is_master']:
                master_text = self._("Master zone")
            elif zone['master_zone'] >= 0:
                try:
                    master_name = self.config.zone_config.zones[zone['master_zone']]['name']
                    master_text = self._("Master: {}").format(master_name)
                except IndexError:
                    pass
            else:
                master_text = self._("No master zone specified")

            if master_text:
                master_label = ttk.Label(name_frame, text=master_text, style='MasterInfo.TLabel')
                master_label.pack(anchor=tk.W)

            # Status indicator next to name
            status_var = StringVar(value="●")
            status_label = ttk.Label(top_frame, textvariable=status_var, foreground='gray', style='Status.TLabel')
            status_label.pack(side=tk.LEFT, padx=20)

            # Button frame below
            button_frame = ttk.Frame(control_frame)
            button_frame.grid(row=row_base + 1, column=col, padx=10, pady=(5, 10))

            # Control button
            button = ttk.Button(button_frame, text=self._("Turn On"), command=lambda z=i: self.toggle_zone(z), style='Large.TButton')
            button.pack()

            self.active_zones[i] = {
                'active': False,
                'button': button,
                'status_var': status_var,
                'status_label': status_label
            }

            if not zone['enabled']:
                button.state(['disabled'])

    def setup_config_panel(self):
        config_frame = ttk.Frame(self.config_frame)
        config_frame.pack(fill=BOTH, expand=True)

        # Add current configuration file display at the top
        if self.config.current_zone_config_file:
            file_frame = ttk.Frame(config_frame)
            file_frame.pack(fill=X, pady=(0, 10))

            file_label = ttk.Label(file_frame, text=self._("Current configuration file:"))
            file_label.pack(anchor=tk.W)

            path_label = ttk.Label(
                file_frame,
                text=os.path.abspath(self.config.current_zone_config_file),
                foreground='#666666',
                wraplength=600  # Wrap long paths
            )
            path_label.pack(anchor=tk.W, pady=(2, 0))

        # MQTT settings - using regular Frame instead of LabelFrame
        mqtt_frame = ttk.Frame(config_frame)
        mqtt_frame.pack(fill=X, pady=5)

        # Create a frame for each row to better organize the MQTT settings
        mqtt_grid = ttk.Frame(mqtt_frame)
        mqtt_grid.pack(fill=X)

        # Configure grid columns
        mqtt_grid.columnconfigure(1, weight=1)  # Make value column expandable
        mqtt_grid.columnconfigure(3, weight=1)  # Make second value column expandable

        # Store all MQTT widgets to control their state
        mqtt_widgets = []
        tls_dependent_widgets = []  # Special list for TLS-dependent widgets

        # Add a variable to track if we're moving between MQTT fields
        self.current_mqtt_values = {}

        def create_mqtt_field(label: str, key: str, row: int, column: int = 0, width: int = 20):
            ttk.Label(mqtt_grid, text=label).grid(row=row, column=column*2, sticky='e', padx=5, pady=2)
            entry = ttk.Entry(mqtt_grid, width=width)
            entry.grid(row=row, column=column*2+1, sticky='ew', padx=5, pady=2)

            # Store the initial value
            initial_value = str(self.config.zone_config.mqtt.get(key, ''))
            self.current_mqtt_values[key] = initial_value
            entry.insert(0, initial_value)

            def on_focus_out(event):
                current_value = entry.get()
                if current_value != self.current_mqtt_values[key]:
                    self.current_mqtt_values[key] = current_value
                    self.update_mqtt_config(key, current_value)

            entry.bind('<FocusOut>', on_focus_out)
            mqtt_widgets.extend([entry])
            return entry


        def update_mqtt_widgets_state(enabled: bool):
            state = ['!disabled'] if enabled else ['disabled']
            for widget in mqtt_widgets:
                widget.state(state)

            # Update MQTT client if state changes
            if enabled != bool(self.mqtt_client):
                if enabled:
                    self.init_mqtt()
                elif self.mqtt_client:
                    self.mqtt_client.disconnect()
                    self.mqtt_client = None


        def update_tls_widgets_state(enabled: bool):
            state = ['!disabled'] if enabled else ['disabled']
            for widget in tls_dependent_widgets:
                widget.state(state)

        # Top row with MQTT Enable and TLS checkboxes
        checkbox_frame = ttk.Frame(mqtt_grid)
        checkbox_frame.grid(row=0, column=0, columnspan=4, sticky='ew', pady=5)
        checkbox_frame.columnconfigure(1, weight=1)  # Make space between checkboxes expandable

        # MQTT Enable checkbox at the left
        mqtt_enable_var = BooleanVar(value=self.config.zone_config.mqtt.get('enabled', False))
        mqtt_enable_cb = ttk.Checkbutton(
            checkbox_frame,
            text=self._("Use MQTT?"),
            variable=mqtt_enable_var,
            command=lambda: [
                self.update_mqtt_config('enabled', mqtt_enable_var.get()),
                update_mqtt_widgets_state(mqtt_enable_var.get())
            ]
        )
        mqtt_enable_cb.pack(side=tk.LEFT, padx=5)

        # Status indicator in the middle
        self.mqtt_status_var = StringVar(value="●")
        self.mqtt_status_label = ttk.Label(
            checkbox_frame,
            textvariable=self.mqtt_status_var,
            foreground='gray'
        )
        self.mqtt_status_label.pack(side=tk.LEFT, padx=5)
        mqtt_widgets.append(self.mqtt_status_label)

        # Status text
        self.mqtt_status_text_var = StringVar(value=self._("Disconnected"))
        self.mqtt_status_text_label = ttk.Label(
            checkbox_frame,
            textvariable=self.mqtt_status_text_var
        )
        self.mqtt_status_text_label.pack(side=tk.LEFT, padx=5)
        mqtt_widgets.append(self.mqtt_status_text_label)

    # Connect button
        self.connect_button = ttk.Button(
            checkbox_frame,
            text=self._("Connect"),
            command=self.handle_mqtt_connect,
            width=10
        )
        self.connect_button.pack(side=tk.LEFT, padx=5)
        mqtt_widgets.append(self.connect_button)

        # TLS setting checkbox at the right
        tls_var = BooleanVar(value=self.config.zone_config.mqtt.get('use_tls', False))
        tls_cb = ttk.Checkbutton(
            checkbox_frame,
            text=self._("Use TLS"),
            variable=tls_var,
            command=lambda: [
                self.update_mqtt_config('use_tls', tls_var.get()),
                update_tls_widgets_state(tls_var.get())
            ]
        )
        tls_cb.pack(side=tk.RIGHT, padx=5)
        mqtt_widgets.append(tls_cb)

        # First column of settings starting at row 1
        create_mqtt_field(self._("Broker:"), 'broker', 1)
        port_entry = create_mqtt_field(self._("Port:"), 'port', 2)
        create_mqtt_field(self._("Username:"), 'username', 3)
        create_mqtt_field(self._("Password:"), 'password', 4)

        # Second column - CA Certificate with browse button
        ca_cert_label = ttk.Label(mqtt_grid, text=self._("CA Certificate Path:"))
        ca_cert_label.grid(row=1, column=2, sticky='e', padx=5, pady=2)

        ca_cert_frame = ttk.Frame(mqtt_grid)
        ca_cert_frame.grid(row=1, column=3, sticky='ew', padx=5, pady=2)
        ca_cert_frame.columnconfigure(0, weight=1)  # Make entry expand

        ca_cert_entry = ttk.Entry(ca_cert_frame)
        ca_cert_entry.grid(row=0, column=0, sticky='ew')
        ca_cert_entry.insert(0, str(self.config.zone_config.mqtt.get('ca_cert_path', '')))
        ca_cert_entry.bind('<FocusOut>', lambda e: self.update_mqtt_config('ca_cert_path', ca_cert_entry.get()))

        def browse_ca_cert():
            filename = filedialog.askopenfilename(
                title=self._("Select CA Certificate"),
                filetypes=[
                    (self._("Certificate files"), "*.pem *.crt *.cer"),
                    (self._("All files"), "*.*")
                ],
                initialdir=os.path.dirname(ca_cert_entry.get()) if ca_cert_entry.get() else os.path.expanduser('~')
            )
            if filename:
                ca_cert_entry.delete(0, tk.END)
                ca_cert_entry.insert(0, filename)
                self.update_mqtt_config('ca_cert_path', filename)

        browse_button = ttk.Button(
            ca_cert_frame,
            text=self._("Browse"),
            command=browse_ca_cert,
            width=10
        )
        browse_button.grid(row=0, column=1, padx=(5, 0))

        # Add CA certificate widgets to both lists
        mqtt_widgets.extend([ca_cert_label])
        tls_dependent_widgets.extend([ca_cert_entry, browse_button])

        # Rest of second column settings
        create_mqtt_field(self._("Client ID:"), 'client_id', 2, column=1)
        create_mqtt_field(self._("Topic Prefix:"), 'topic_prefix', 3, column=1)
        create_mqtt_field(self._("Status Update Interval:"), 'status_update_interval', 4, column=1)

        # Convert port and interval entries to integers on update
        def validate_int_entry(entry, key):
            try:
                value = int(entry.get())
                if str(value) != self.current_mqtt_values[key]:
                    self.current_mqtt_values[key] = str(value)
                    self.update_mqtt_config(key, value)
            except ValueError:
                # Restore previous value
                entry.delete(0, 'end')
                entry.insert(0, self.current_mqtt_values[key])

        # When creating the port entry:
        self.current_mqtt_values['port'] = str(self.config.zone_config.mqtt.get('port', 0))
        port_entry.bind('<FocusOut>', lambda e: validate_int_entry(port_entry, 'port'))

        # Set initial states
        update_mqtt_widgets_state(mqtt_enable_var.get())
        update_tls_widgets_state(tls_var.get())

        # Add separator between MQTT and other settings
        ttk.Separator(config_frame, orient='horizontal').pack(fill=X, pady=10)

        # General settings
        general_frame = ttk.LabelFrame(config_frame, text=self._("General Settings"), padding=10)
        general_frame.pack(fill=X, pady=5)

        # Auto-open master setting
        auto_master_var = BooleanVar(value=self.config.zone_config.general['open_master_automatically'])
        auto_master_cb = ttk.Checkbutton(
            general_frame,
            text=self._("Auto-open master zone when a dependent zone is turned on"),
            variable=auto_master_var
        )
        auto_master_cb.configure(command=lambda v=auto_master_var: self.update_general_config('open_master_automatically', v.get()))
        auto_master_cb.pack(anchor=tk.W)

        # Auto-close master setting
        close_master_var = BooleanVar(value=self.config.zone_config.general.get('close_master_automatically', True))
        close_master_cb = ttk.Checkbutton(
            general_frame,
            text=self._("Close master automatically when all dependent zones are off"),
            variable=close_master_var
        )
        close_master_cb.configure(command=lambda v=close_master_var: self.update_general_config('close_master_automatically', v.get()))
        close_master_cb.pack(anchor=tk.W)

        # Auto-close dependent zones setting
        close_dependent_var = BooleanVar(value=self.config.zone_config.general.get('close_dependent_automatically', True))
        close_dependent_cb = ttk.Checkbutton(
            general_frame,
            text=self._("Close dependent zones automatically when master is turned off"),
            variable=close_dependent_var
        )
        close_dependent_cb.configure(command=lambda v=close_dependent_var: self.update_general_config('close_dependent_automatically', v.get()))
        close_dependent_cb.pack(anchor=tk.W)

        # Zone management buttons
        button_frame = ttk.Frame(config_frame)
        button_frame.pack(fill=X, pady=5)

        add_button = ttk.Button(
            button_frame,
            text=self._("Add Zone"),
            command=self.add_zone
        )
        add_button.pack(side=tk.LEFT, padx=5)

        remove_button = ttk.Button(
            button_frame,
            text=self._("Remove Last Zone"),
            command=self.remove_zone
        )
        remove_button.pack(side=tk.LEFT, padx=5)

        # Update button states based on zone count
        zone_count = len(self.config.zone_config.zones)
        if zone_count >= 8:
            add_button.state(['disabled'])
        if zone_count <= 1:
            remove_button.state(['disabled'])

        # Zone settings
        zones_frame = ttk.Frame(config_frame)
        zones_frame.pack(fill=BOTH, expand=True, pady=5)

        def create_name_callback(zone_idx, var):
            def callback(*args):
                self.update_zone_config(zone_idx, 'name', var.get())
                self.after(100, self.refresh_ui)
            return callback

        # Create configuration controls for each zone
        for i, zone in enumerate(self.config.zone_config.zones):
            zone_frame = ttk.Frame(zones_frame)
            zone_frame.pack(fill=X, pady=5)

            def create_zone_controls(idx, zone_data):
                # Store references to widgets that need to be enabled/disabled
                zone_widgets = {}

                # Zone name entry
                name_var = StringVar(value=zone_data['name'])
                name_entry = ttk.Entry(zone_frame, textvariable=name_var, width=20)
                name_entry.pack(side=tk.LEFT, padx=5)
                name_var.trace_add('write', create_name_callback(idx, name_var))
                zone_widgets['name_entry'] = name_entry

                def on_enabled_change():
                    is_enabled = enabled_var.get()

                    # First update the enabled state
                    self.update_zone_config(idx, 'enabled', is_enabled)

                    if not is_enabled:
                        # When disabling, reset master-related settings
                        self.update_zone_config(idx, 'master_zone', -1)  # Set to None
                        self.update_zone_config(idx, 'is_master', False)  # Remove master status
                        is_master_var.set(False)  # Update checkbox state

                        # If this was a master zone, need to reset any zones that were using it
                        if zone_data['is_master']:
                            for i, other_zone in enumerate(self.config.zone_config.zones):
                                if other_zone['master_zone'] == idx:
                                    self.update_zone_config(i, 'master_zone', -1)

                    # Update widget states
                    for widget in zone_widgets.values():
                        if widget.winfo_exists():  # Check if widget still exists
                            if is_enabled:
                                widget.state(['!disabled'])
                            else:
                                widget.state(['disabled'])

                    # Refresh UI to reflect all changes
                    self.refresh_ui()

                # Zone enabled checkbox
                enabled_var = BooleanVar(value=zone_data['enabled'])
                enabled_cb = ttk.Checkbutton(
                    zone_frame,
                    text=self._("Enabled"),
                    variable=enabled_var
                )
                enabled_cb.configure(command=on_enabled_change)
                enabled_cb.pack(side=tk.LEFT, padx=5)

                # Master zone checkbox
                is_master_var = BooleanVar(value=zone_data['is_master'])
                is_master_cb = ttk.Checkbutton(
                    zone_frame,
                    text=self._("Is master"),
                    variable=is_master_var
                )
                is_master_cb.configure(command=lambda v=is_master_var, z=idx: self.handle_master_change(z, v.get()))
                is_master_cb.pack(side=tk.LEFT, padx=5)
                zone_widgets['is_master_cb'] = is_master_cb

                # Master zone selection (not for master zones)
                if not zone_data['is_master']:
                    # Create mapping of values to display names
                    master_zones = {-1: self._("None")}
                    master_zones.update({
                        idx: z['name']
                        for idx, z in enumerate(self.config.zone_config.zones)
                        if z['is_master']
                    })

                    # Create the combo box with display names
                    master_var = StringVar()
                    master_combo = ttk.Combobox(
                        zone_frame,
                        values=list(master_zones.values()),
                        state='readonly',
                        width=10
                    )

                    # Set initial value using the display name
                    # If current master_zone isn't valid anymore, reset to "None"
                    if zone_data['master_zone'] not in master_zones:
                        zone_data['master_zone'] = -1
                    master_combo.set(master_zones[zone_data['master_zone']])

                    # Create reverse lookup for converting display names back to values
                    display_to_value = {name: value for value, name in master_zones.items()}

                    def on_master_select(event):
                        # Convert display name back to numerical value
                        display_name = master_combo.get()
                        value = display_to_value[display_name]
                        self.update_zone_config(idx, 'master_zone', value)
                        # Add refresh call here to update the control panel
                        self.refresh_ui()

                    master_combo.bind('<<ComboboxSelected>>', on_master_select)
                    master_combo.pack(side=tk.RIGHT, padx=5)
                    zone_widgets['master_combo'] = master_combo
                    ttk.Label(zone_frame, text=self._("or select master:")).pack(side=tk.RIGHT)

                    # Set initial states based on enabled status
                    if not zone_data['enabled']:
                        for widget in zone_widgets.values():
                            widget.state(['disabled'])

            create_zone_controls(i, zone)

    def handle_master_change(self, zone_id, is_master):
        """Handle changes to the is_master status of a zone"""
        # If zone is being un-marked as master, reset dependent zones
        if not is_master:
            for i, zone in enumerate(self.config.zone_config.zones):
                if zone['master_zone'] == zone_id:
                    self.config.zone_config.zones[i]['master_zone'] = -1

        # Update the zone's master status
        self.config.zone_config.zones[zone_id]['is_master'] = is_master

        # Refresh the UI
        self.refresh_ui()

    def activate_zone(self, zone_id, skip_mqtt=False):
        """
        Activate a zone and handle master zone relationships.

        Args:
            zone_id: ID of the zone to activate
            skip_mqtt: If True, don't publish MQTT messages
        """
        zone_info = self.active_zones[zone_id]
        if zone_info['active']:
            return

        zone_info['active'] = True
        zone_info['button'].configure(text=self._("Turn Off"))
        zone_info['status_var'].set("●")
        zone_info['status_label'].configure(foreground='green')

        if not skip_mqtt:
            self.publish_zone_command(zone_id, True)

    def toggle_zone(self, zone_id):
        """Toggle a zone's state and handle master zone relationships"""
        zone_info = self.active_zones[zone_id]
        new_state = not zone_info['active']

        # Check if we need to handle master zone when turning on
        if new_state and not self.config.zone_config.zones[zone_id]['is_master']:
            master_zone = self.config.zone_config.zones[zone_id]['master_zone']
            if master_zone >= 0 and self.config.zone_config.general['open_master_automatically']:
                # Activate master zone first, with skip_mqtt=False to send command
                self.activate_zone(master_zone)

        # Now handle the actual zone
        if new_state:
            self.activate_zone(zone_id)
        else:
            self.deactivate_zone(zone_id)

    def deactivate_zone(self, zone_id, skip_mqtt=False):
        """
        Deactivate a zone and handle master zone relationships.
        If the zone is a master and auto-close is enabled, also deactivate all dependent zones.
        """
        if not self.active_zones[zone_id]['active']:
            return

        zone_info = self.active_zones[zone_id]
        zone = self.config.zone_config.zones[zone_id]

        # If this is a master zone and auto-close dependent is enabled,
        # first deactivate all dependent zones
        if (zone['is_master'] and
            self.config.zone_config.general.get('close_dependent_automatically', True)):
            # Find and deactivate all dependent zones
            for dependent_id, dependent_zone in enumerate(self.config.zone_config.zones):
                if (dependent_zone['master_zone'] == zone_id and
                    self.active_zones[dependent_id]['active']):
                    # Deactivate UI state first
                    dependent_info = self.active_zones[dependent_id]
                    dependent_info['active'] = False
                    dependent_info['button'].configure(text=self._("Turn On"))
                    dependent_info['status_var'].set("●")
                    dependent_info['status_label'].configure(foreground='gray')

                    # Send MQTT command if not skipped
                    if not skip_mqtt:
                        self.publish_zone_command(dependent_id, False)

        # Now deactivate this zone
        zone_info['active'] = False
        zone_info['button'].configure(text=self._("Turn On"))
        zone_info['status_var'].set("●")
        zone_info['status_label'].configure(foreground='gray')

        if not skip_mqtt:
            self.publish_zone_command(zone_id, False)

        # Check other masters (not for dependent zone deactivation)
        if not zone['is_master']:
            self.check_and_deactivate_masters(zone_id, skip_mqtt)

    def check_and_deactivate_masters(self, changed_zone_id, skip_mqtt=False):
        """
        Check if any master zones should be deactivated and handle their deactivation.
        """
        if self.config.zone_config.general.get('close_master_automatically', True):
            for master_id, master_zone in enumerate(self.config.zone_config.zones):
                if (master_zone['is_master'] and
                    self.active_zones[master_id]['active'] and
                    master_id != changed_zone_id):
                    if self.should_deactivate_master(master_id):
                        # Deactivate the master zone's state locally
                        zone_info = self.active_zones[master_id]
                        zone_info['active'] = False
                        zone_info['button'].configure(text=self._("Turn On"))
                        zone_info['status_var'].set("●")
                        zone_info['status_label'].configure(foreground='gray')

                        if not skip_mqtt:
                            self.publish_zone_command(master_id, False)

    def check_master_dependencies(self, master_id):
        """Check if any dependent zones are still active for a given master zone"""
        for i, zone in enumerate(self.config.zone_config.zones):
            if zone['master_zone'] == master_id and self.active_zones[i]['active']:
                return True
        return False

    def should_deactivate_master(self, master_id):
        """Check if a master should be deactivated"""
        # Check if any zones (including other masters) that depend on this master are active
        return not any(
            zone['master_zone'] == master_id and self.active_zones[i]['active']
            for i, zone in enumerate(self.config.zone_config.zones)
        )

    def refresh_ui(self):
        # Clear existing widgets
        for widget in self.control_frame.winfo_children():
            widget.destroy()
        for widget in self.config_frame.winfo_children():
            widget.destroy()

        # Recreate panels
        self.setup_control_panel()
        self.setup_config_panel()

    def update_zone_config(self, zone_id, field, value):
        self.config.zone_config.zones[zone_id][field] = value
        # If changing is_master status, update UI to reflect changes
        if field == 'is_master':
            self.refresh_ui()

    def update_general_config(self, field, value):
        self.config.zone_config.general[field] = value

    def add_zone(self):
        """Add a new zone to the configuration"""
        if len(self.config.zone_config.zones) >= 8:
            return

        # Create new zone with default values and next available index as part of name
        new_zone = {
            'name': f"Zone {len(self.config.zone_config.zones)}",
            'enabled': True,
            'master_zone': -1,
            'is_master': False
        }

        # Add to configuration
        self.config.zone_config.zones.append(new_zone)

        # Refresh UI
        self.refresh_ui()

    def remove_zone(self):
        """Remove the last zone from the configuration"""
        if len(self.config.zone_config.zones) <= 1:
            return

        last_zone = self.config.zone_config.zones[-1]
        # If this was a master zone, reset any zones that were using it
        if last_zone['is_master']:
            last_idx = len(self.config.zone_config.zones) - 1
            for zone in self.config.zone_config.zones[:-1]:  # Exclude the zone being removed
                if zone['master_zone'] == last_idx:
                    zone['master_zone'] = -1

        # Remove the zone
        self.config.zone_config.zones.pop()

        # Refresh UI
        self.refresh_ui()


    def handle_mqtt_connect(self):
        """Handle MQTT connect button click"""
        self.init_mqtt()

    def update_mqtt_status(self, connected: bool):
        """Update MQTT status indicators"""
        if connected:
            self.mqtt_status_var.set("●")
            self.mqtt_status_label.configure(foreground='green')
            self.mqtt_status_text_var.set(self._("Connected"))
            self.connect_button.configure(text=self._("Disconnect"))
            self.connect_button.configure(command=self.handle_mqtt_disconnect)
        else:
            self.mqtt_status_var.set("●")
            self.mqtt_status_label.configure(foreground='red')
            self.mqtt_status_text_var.set(self._("Disconnected"))
            self.connect_button.configure(text=self._("Connect"))
            self.connect_button.configure(command=self.handle_mqtt_connect)

    def handle_mqtt_disconnect(self):
        """Handle MQTT disconnect button click"""
        if self.mqtt_client:
            self.mqtt_client.disconnect()
            self.update_mqtt_status(False)

    def update_mqtt_config(self, field: str, value: Any):
        """Update MQTT configuration field"""
        self.config.zone_config.mqtt[field] = value
        # Disconnect if we're changing configuration
        if self.mqtt_client and self.mqtt_client.connected:
            self.mqtt_client.disconnect()

    def handle_mqtt_state_change(self, zone_id: int, is_on: bool):
        """Handle zone state changes from MQTT"""
        if zone_id not in self.active_zones:
            return

        if is_on:
            # If turning on a dependent zone, check if we need to activate its master
            if not self.config.zone_config.zones[zone_id]['is_master']:
                master_zone = self.config.zone_config.zones[zone_id]['master_zone']
                if master_zone >= 0 and self.config.zone_config.general['open_master_automatically']:
                    if not self.active_zones[master_zone]['active']:
                        self.activate_zone(master_zone, skip_mqtt=True)
                        self.publish_zone_command(master_zone, True)

            # Now activate the zone itself
            self.activate_zone(zone_id, skip_mqtt=True)
        else:
            zone = self.config.zone_config.zones[zone_id]

            # If this is a master zone being turned off and auto-close dependent is enabled,
            # deactivate all dependent zones first
            if (zone['is_master'] and
                self.config.zone_config.general.get('close_dependent_automatically', True)):
                # First collect all dependent zones that need to be deactivated
                dependent_zones = [
                    (dependent_id, dependent_zone)
                    for dependent_id, dependent_zone in enumerate(self.config.zone_config.zones)
                    if dependent_zone['master_zone'] == zone_id and self.active_zones[dependent_id]['active']
                ]

                # Deactivate each dependent zone and send command
                for dependent_id, _ in dependent_zones:
                    self.deactivate_zone(dependent_id, skip_mqtt=True)
                    self.publish_zone_command(dependent_id, False)

            # Now deactivate the master zone itself, but don't send an MQTT command since we received this state from MQTT
            self.deactivate_zone(zone_id, skip_mqtt=True)

    def publish_zone_command(self, zone_id: int, state: bool):
        """Publish zone command to MQTT if enabled"""
        if self.mqtt_client and self.mqtt_client.connected:
            self.mqtt_client.publish_zone_command(zone_id, state)