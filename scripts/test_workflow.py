import urllib.request, json, time

base = 'http://127.0.0.1:8000/api/v1'

def post(url, data={}):
    req = urllib.request.Request(f'{base}{url}', data=json.dumps(data).encode(), headers={'Content-Type': 'application/json'}, method='POST')
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read().decode())

def get(url):
    req = urllib.request.Request(f'{base}{url}')
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read().decode())

# 1. Reset
print('1. Reset simulation')
res_reset = post('/simulation/reset')
print('Reset result:', res_reset['status'])

# 2. Run Scenario (auto_verify=False)
print('2. Trigger Run Scenario')
state = post('/orchestration/run-scenario', {'scenario_name': 'test', 'auto_verify': False})
inc = state.get('active_incident')
print(f'Active incident created: {inc["incident_id"]}, Status: {inc["status"]}, Location: {inc["location_node"]}')

# 3. Verify Incident
print('3. Verify Incident')
v_inc = post(f'/incidents/{inc["incident_id"]}/verify', {'verified': True, 'operator_id': 'OP-01', 'notes': 'Verified test'})
print(f'Incident verified. Status: {v_inc["status"]}, Assigned units: {v_inc["assigned_unit_ids"]}')

# 4. Dispatch Incident
print('4. Dispatch Incident')
d_inc = post(f'/incidents/{inc["incident_id"]}/dispatch')
print(f'Incident dispatched. Status: {d_inc["status"]}')

# Check unit status right after dispatch
units_0 = get('/simulation/tick')
amb = [u for u in units_0 if u['unit_id'] == 'AMB-01'][0]
print(f'AMB-01 status: {amb["status"]}, Start lat: {amb["latitude"]:.5f}, lon: {amb["longitude"]:.5f}, ETA: {amb["eta_seconds"]}s, Geom points: {len(amb.get("route_geometry") or [])}')

# 5. Simulate ticks over time
print('5. Ticking simulation at 20x speed...')
for step in range(5):
    time.sleep(1)
    units_t = get('/simulation/tick?speed=20.0')
    amb_t = [u for u in units_t if u['unit_id'] == 'AMB-01'][0]
    print(f'Tick {step+1}: AMB-01 status={amb_t["status"]} lat={amb_t["latitude"]:.5f} lon={amb_t["longitude"]:.5f} eta={amb_t["eta_seconds"]}s')

# Check incident status after arrival
state_final = get('/orchestration/state')
print(f'Final orchestration stage: {state_final["stage"]}, status: {state_final["status"]}')
print(f'Latest agent log: {state_final["agent_logs"][-1]["action"] if state_final.get("agent_logs") else "None"}')

# 6. Reset test
print('6. Testing reset')
post('/simulation/reset')
units_reset = get('/resources/')
amb_r = [u for u in units_reset if u['unit_id'] == 'AMB-01'][0]
print(f'AMB-01 after reset: node={amb_r["current_node"]}, station={amb_r["station_node"]}, status={amb_r["status"]}, route_geom={len(amb_r.get("route_geometry") or [])}')
state_reset = get('/orchestration/state')
print(f'Active routes after reset: {len(state_reset["active_routes"])}, Active incident after reset: {state_reset["active_incident"]}')

