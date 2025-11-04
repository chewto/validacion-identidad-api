import cpuinfo

# Get a dictionary containing various CPU details
cpu_info = cpuinfo.get_cpu_info()

# Access specific information
processor_name = cpu_info.get('brand_raw')
architecture = cpu_info.get('arch')
hz_advertised = cpu_info.get('hz_advertised_friendly')
hz_actual = cpu_info.get('hz_actual_friendly')

print(f"Processor Name: {processor_name}")
print(f"Architecture: {architecture}")
print(f"Advertised Frequency: {hz_advertised}")
print(f"Actual Frequency: {hz_actual}")

# To see all available keys and their values:
# for key, value in cpu_info.items():
#     print(f"{key}: {value}")