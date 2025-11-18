"""
Calculate sum of three numbers
"""
import json
from servers.calculator.add import calculator_add

# Add first two numbers
result1_json = calculator_add(a=3, b=3)
result1 = json.loads(result1_json)["result"]

# Add third number
result2_json = calculator_add(a=result1, b=3)
result2 = json.loads(result2_json)["result"]

print(f"Answer: {result2}")
