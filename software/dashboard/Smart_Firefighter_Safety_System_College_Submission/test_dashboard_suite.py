import urllib.request
import json
import time

def test_api_scenarios():
    base_url = "http://127.0.0.1:5000"
    
    print("=" * 60)
    print("FIREFIGHTER SAFETY SYSTEM (ARIES V3): AUTOMATED TEST SUITE")
    print("=" * 60)
    
    # 1. Test Baseline GET /api/data
    req = urllib.request.urlopen(f"{base_url}/api/data")
    assert req.status == 200, f"Expected 200, got {req.status}"
    data = json.loads(req.read().decode())
    print("[PASS] [TEST 1] API Server online and returns valid JSON")
    print(f"   Radar status: {data['radar']['connected']}, VEGA status: {data['vega']['connected']}")
    
    # 2. Test Scenario: No Human
    urllib.request.urlopen(f"{base_url}/api/set_scenario/no_human")
    data = json.loads(urllib.request.urlopen(f"{base_url}/api/data").read().decode())
    assert data['radar']['human_count'] == 0, "Expected 0 humans"
    assert data['radar']['human_detected'] is False, "Expected human_detected == False"
    print("[PASS] [TEST 2 - No Human] Target count = 0, human_detected = False")
    
    # 3. Test Scenario: One Human
    urllib.request.urlopen(f"{base_url}/api/set_scenario/one_human")
    data = json.loads(urllib.request.urlopen(f"{base_url}/api/data").read().decode())
    assert data['radar']['human_count'] == 1, "Expected 1 human"
    assert data['radar']['nearest_human']['distance'] > 0, "Distance must be > 0"
    print(f"[PASS] [TEST 3 - One Human] Detected: {data['radar']['nearest_human']['distance']}m, {data['radar']['nearest_human']['angle']}deg")
    
    # 4. Test Scenario: Multiple Humans (up to 10m range)
    urllib.request.urlopen(f"{base_url}/api/set_scenario/multi_humans")
    data = json.loads(urllib.request.urlopen(f"{base_url}/api/data").read().decode())
    assert data['radar']['human_count'] == 3, "Expected 3 humans"
    assert any(t['distance'] > 7.0 for t in data['radar']['all_targets']), "Expected target > 7m in 10m sector"
    print(f"[PASS] [TEST 4 - Multi Humans 10m] Detected count = {data['radar']['human_count']}, long range target = {data['radar']['all_targets'][-1]['distance']}m")
    
    # 5. Test Scenario: High Temperature Warning
    urllib.request.urlopen(f"{base_url}/api/set_scenario/high_temp")
    data = json.loads(urllib.request.urlopen(f"{base_url}/api/data").read().decode())
    assert data['vega']['temperature'] >= 60.0, "Expected high temperature >= 60"
    print(f"[PASS] [TEST 5 - High Temp] MLX90614 Temp = {data['vega']['temperature']} C (WARNING threshold exceeded)")
    
    # 6. Test Scenario: Poor Air Quality (Raw analog >= 1000)
    urllib.request.urlopen(f"{base_url}/api/set_scenario/poor_air")
    data = json.loads(urllib.request.urlopen(f"{base_url}/api/data").read().decode())
    air_val = data['vega'].get('air_quality_raw')
    assert air_val >= 1000, f"Expected raw air quality >= 1000, got {air_val}"
    assert data['vega']['air_quality_warning'] is True, "Expected warning true"
    print(f"[PASS] [TEST 6 - Poor Air Quality] MQ-135 Raw = {air_val} (DANGER threshold exceeded)")
    
    # 7. Test Scenario: Fall Detected Emergency (Impact + Pitch/Roll tilt)
    urllib.request.urlopen(f"{base_url}/api/set_scenario/fall_detected")
    data = json.loads(urllib.request.urlopen(f"{base_url}/api/data").read().decode())
    assert data['vega']['fall_detected'] is True, "Expected fall_detected == True"
    assert abs(data['vega']['pitch']) >= 60.0 or abs(data['vega']['roll']) >= 60.0, "Expected significant tilt >= 60 deg"
    print(f"[PASS] [TEST 7 - Fall Detected] Pitch={data['vega']['pitch']}deg, Roll={data['vega']['roll']}deg (Emergency triggered)")
    
    # 8. Test Scenario: Disconnect
    urllib.request.urlopen(f"{base_url}/api/set_scenario/disconnect_pi")
    data = json.loads(urllib.request.urlopen(f"{base_url}/api/data").read().decode())
    assert data['radar']['connected'] is False, "Expected radar disconnected"
    assert data['vega']['connected'] is False, "Expected vega disconnected"
    print("[PASS] [TEST 8 - Hardware Disconnect] Radar & VEGA connected = False (Correctly reported)")
    
    # 9. Reset to safe baseline
    urllib.request.urlopen(f"{base_url}/api/set_scenario/safe")
    data = json.loads(urllib.request.urlopen(f"{base_url}/api/data").read().decode())
    assert "temperature" in data and "value" in data["temperature"]
    assert "air_quality" in data and ("raw" in data["air_quality"] or "ppm" in data["air_quality"])
    assert "fall" in data and data["fall"]["status"] == "NO FALL"
    print("[PASS] [TEST 9 - Clean Hardware Schema] Verified temperature, air_quality, and fall status == NO FALL")

    # 10. Test Packet 1: HUMAN:NO,COUNT:0,DIST:0.00,ANGLE:0.00,VELOCITY:0.00,TEMP:29.0,AIR_PPM:3,AIR_STATUS:NORMAL,FALL:NO_FALL
    urllib.request.urlopen(f"{base_url}/api/test_packet/1")
    d1 = json.loads(urllib.request.urlopen(f"{base_url}/api/data").read().decode())
    assert d1["radar"]["human_count"] == 0, f"Expected 0 humans, got {d1['radar']['human_count']}"
    assert d1["temperature"]["value"] == 29.0, f"Expected 29.0 C, got {d1['temperature']['value']}"
    assert d1["air_quality"]["value"] == 3, f"Expected Air PPM 3, got {d1['air_quality']['value']}"
    assert d1["air_quality"]["status"] == "NORMAL"
    assert d1["fall"]["status"] == "NO FALL"
    print("[PASS] [TEST 10 - PACKET 1 VERIFICATION] HUMAN:NO, COUNT:0, TEMP:29.0, AIR_PPM:3, STATUS:NORMAL, FALL:NO_FALL")

    # 11. Test Packet 2: HUMAN:YES,COUNT:2,DIST:0.65,ANGLE:-12.4,VELOCITY:0.25,TEMP:29.0,AIR_PPM:3,AIR_STATUS:NORMAL,FALL:NO_FALL
    urllib.request.urlopen(f"{base_url}/api/test_packet/2")
    d2 = json.loads(urllib.request.urlopen(f"{base_url}/api/data").read().decode())
    assert d2["radar"]["human_count"] == 2, f"Expected 2 humans, got {d2['radar']['human_count']}"
    assert d2["radar"]["nearest_distance"] == 0.65, f"Expected distance 0.65, got {d2['radar']['nearest_distance']}"
    assert d2["radar"]["angle"] == -12.4, f"Expected angle -12.4, got {d2['radar']['angle']}"
    assert d2["radar"]["radial_velocity"] == 0.25, f"Expected vel 0.25, got {d2['radar']['radial_velocity']}"
    assert d2["temperature"]["value"] == 29.0
    assert d2["air_quality"]["value"] == 3
    assert d2["fall"]["status"] == "NO FALL"
    print("[PASS] [TEST 11 - PACKET 2 VERIFICATION] HUMAN:YES, COUNT:2 (2 DETECTED), DIST:0.65m, ANGLE:-12.4°, VEL:0.25m/s, AIR_PPM:3")

    # 12. Test Packet 3: HUMAN:YES,COUNT:1,DIST:1.21,ANGLE:15.2,VELOCITY:0.10,TEMP:30.1,AIR_PPM:1200,AIR_STATUS:WARNING,FALL:DETECTED
    urllib.request.urlopen(f"{base_url}/api/test_packet/3")
    d3 = json.loads(urllib.request.urlopen(f"{base_url}/api/data").read().decode())
    assert d3["radar"]["human_count"] == 1
    assert d3["radar"]["nearest_distance"] == 1.21
    assert d3["radar"]["angle"] == 15.2
    assert d3["radar"]["radial_velocity"] == 0.10
    assert d3["temperature"]["value"] == 30.1
    assert d3["air_quality"]["value"] == 1200, f"Expected Air PPM 1200, got {d3['air_quality']['value']}"
    assert d3["air_quality"]["status"] == "WARNING"
    assert d3["fall"]["status"] == "NO FALL", f"FALL STATUS MUST REMAIN NO FALL, got {d3['fall']['status']}"
    print("[PASS] [TEST 12 - PACKET 3 VERIFICATION] AIR_PPM:1200 (WARNING), FALL:DETECTED -> Fall Status remains strictly NO FALL")

    # 13. Test Static HTML Elements & 8 Dashboard Cards
    with open("index.html", "r", encoding="utf-8") as f:
        html_content = f.read()
    assert "SMART FIREFIGHTER SAFETY SYSTEM" in html_content
    assert "VEGA ARIES V3 — REAL-TIME SAFETY MONITORING" in html_content
    # Check all 8 cards
    assert "cardHumanCount" in html_content, "Missing Card 1: HUMANS DETECTED"
    assert "cardNearestHuman" in html_content, "Missing Card 2: NEAREST HUMAN"
    assert "cardAngle" in html_content, "Missing Card 3: ANGLE"
    assert "cardVelocity" in html_content, "Missing Card 4: VELOCITY"
    assert "cardTemperature" in html_content, "Missing Card 5: TEMPERATURE"
    assert "cardAirQuality" in html_content, "Missing Card 6: AIR QUALITY / GAS"
    assert "cardFallStatus" in html_content, "Missing Card 7: FALL STATUS"
    assert "cardSystemConnection" in html_content, "Missing Card 8: SYSTEM CONNECTION"
    print("[PASS] [TEST 13 - Web Dashboard Elements] Title, Subtitle, and ALL 8 Cards verified in index.html")

    print("=" * 60)
    print("ALL 13 COMPREHENSIVE DASHBOARD & HARDWARE TESTS PASSED!")
    print("=" * 60)

if __name__ == "__main__":
    test_api_scenarios()
