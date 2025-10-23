import json

# Read the data
with open('/mnt/e/rmd..txt', 'r') as f:
    content = f.read()

# Split into device records
devices = []
for line in content.strip().split('\n'):
    if line.strip():
        try:
            data = json.loads(line)
            if 'payload' in data and 'device' in data['payload']:
                device = data['payload']['device']
                devices.append(device)
        except:
            pass

# Group devices by type
device_types = {}
for device in devices:
    capabilities = device.get('capabilities', [])
    device_type = None
    device_name = None
    for cap in capabilities:
        if cap.get('name') == 'DEVICE_TYPE_LOC':
            device_type = cap.get('value')
        if cap.get('name') == 'NAME_DEVICE_LOC':
            device_name = cap.get('value')
    
    if device_type:
        if device_type not in device_types:
            device_types[device_type] = {'devices': [], 'cmds': set(), 'evts': set()}
        
        device_types[device_type]['devices'].append(device_name)
        
        # Extract CMD and EVT capabilities
        for cap in capabilities:
            name = cap.get('name', '')
            if name.endswith('_CMD'):
                device_types[device_type]['cmds'].add(name)
            elif name.endswith('_EVT'):
                device_types[device_type]['evts'].add(name)

# Print results
for dtype in sorted(device_types.keys()):
    print(f"\n=== DEVICE TYPE {dtype} ===")
    print(f"Devices: {device_types[dtype]['devices']}")
    print(f"\nCMD Capabilities ({len(device_types[dtype]['cmds'])}):")
    for cmd in sorted(device_types[dtype]['cmds']):
        print(f"  {cmd}")
    print(f"\nEVT Capabilities ({len(device_types[dtype]['evts'])}):")
    for evt in sorted(device_types[dtype]['evts']):
        print(f"  {evt}")
