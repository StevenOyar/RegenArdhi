#!/usr/bin/env python3
"""
Quick test to check if insights blueprint is registered
Run this: python test_insights_route.py
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("🔍 Testing Insights Blueprint Registration...\n")

# Test 1: Import the app
print("1️⃣ Importing Flask app...")
try:
    from run import app
    print("   ✅ App imported successfully")
except Exception as e:
    print(f"   ❌ Failed to import app: {e}")
    sys.exit(1)

# Test 2: Check if blueprint exists
print("\n2️⃣ Checking if insights blueprint is registered...")
try:
    blueprints = list(app.blueprints.keys())
    print(f"   📦 Registered blueprints: {blueprints}")
    
    if 'insights' in blueprints:
        print("   ✅ Insights blueprint is registered!")
    else:
        print("   ❌ Insights blueprint NOT registered!")
        print("   💡 Available blueprints:", blueprints)
except Exception as e:
    print(f"   ❌ Error checking blueprints: {e}")

# Test 3: List all routes
print("\n3️⃣ Checking registered routes...")
insights_routes = []
all_routes = []

for rule in app.url_map.iter_rules():
    route_str = str(rule)
    all_routes.append(route_str)
    if 'insights' in route_str.lower():
        insights_routes.append(route_str)

print(f"   📊 Total routes: {len(all_routes)}")
print(f"   🎯 Insights routes: {len(insights_routes)}")

if insights_routes:
    print("\n   ✅ Found insights routes:")
    for route in insights_routes:
        methods = [m for m in app.url_map._rules_by_endpoint.get(route, []) if m != 'HEAD' and m != 'OPTIONS']
        print(f"      • {route}")
else:
    print("\n   ❌ NO insights routes found!")
    print("\n   📋 Sample of registered routes:")
    for route in all_routes[:10]:
        print(f"      • {route}")

# Test 4: Try to access insights blueprint directly
print("\n4️⃣ Attempting to access insights blueprint...")
try:
    from app.insights import insights_bp
    print(f"   ✅ Blueprint imported: {insights_bp}")
    print(f"   📍 Blueprint name: {insights_bp.name}")
    print(f"   📍 URL prefix: {insights_bp.url_prefix}")
    print(f"   📍 Blueprint routes: {list(insights_bp.deferred_functions)[:5]}")
except Exception as e:
    print(f"   ❌ Failed to import insights blueprint: {e}")
    import traceback
    traceback.print_exc()

# Test 5: Check if insights.html template exists
print("\n5️⃣ Checking if template exists...")
template_paths = [
    'templates/insights.html',
    'app/templates/insights.html',
]

for path in template_paths:
    if os.path.exists(path):
        print(f"   ✅ Found template: {path}")
        break
else:
    print(f"   ⚠️  Template not found in: {template_paths}")

# Final recommendation
print("\n" + "="*70)
print("📊 DIAGNOSIS COMPLETE")
print("="*70)

if insights_routes:
    print("✅ Insights blueprint is properly configured!")
    print(f"🌐 Visit: http://localhost:5000{insights_routes[0]}")
else:
    print("❌ PROBLEM DETECTED: Insights blueprint not registered")
    print("\n🔧 TO FIX:")
    print("   1. Check app/__init__.py for insights import")
    print("   2. Ensure no errors during blueprint registration")
    print("   3. Verify app/insights.py exists and has insights_bp")
    print("   4. Restart Flask: python run.py")

print("="*70 + "\n")