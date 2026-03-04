"""
Check GPU & CUDA availability for RTX 3050
"""
import subprocess
import sys

print("=" * 70)
print("GPU & CUDA CHECK")
print("=" * 70)

# Check NVIDIA GPU
print("\n[1/3] NVIDIA GPU Check...")
try:
    result = subprocess.run(['nvidia-smi'], capture_output=True, text=True)
    if result.returncode == 0:
        print("✅ NVIDIA GPU detected!")
        # Parse output
        lines = result.stdout.split('\n')
        for line in lines:
            if 'RTX' in line or 'CUDA Version' in line:
                print(f"   {line.strip()}")
    else:
        print("❌ nvidia-smi failed. GPU driver may not be installed.")
except FileNotFoundError:
    print("❌ nvidia-smi not found. Please install NVIDIA GPU driver.")
    print("   Download: https://www.nvidia.com/Download/index.aspx")

# Check PyTorch availability
print("\n[2/3] PyTorch Check...")
try:
    import torch
    print(f"✅ PyTorch version: {torch.__version__}")
    print(f"   CUDA available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"   CUDA version: {torch.version.cuda}")
        print(f"   GPU name: {torch.cuda.get_device_name(0)}")
        print(f"   GPU memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB")
    else:
        print("⚠️  CUDA not available in PyTorch!")
        print("   Need to install PyTorch with CUDA support.")
except ImportError:
    print("❌ PyTorch not installed yet.")

# Determine CUDA version and PyTorch install command
print("\n[3/3] Installation Recommendation...")
try:
    result = subprocess.run(['nvidia-smi'], capture_output=True, text=True)
    output = result.stdout
    
    # Extract CUDA version from nvidia-smi
    if 'CUDA Version: 12.1' in output or 'CUDA Version: 12' in output:
        cuda_version = "12.1"
        torch_cmd = "pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121"
    elif 'CUDA Version: 11.8' in output or 'CUDA Version: 11' in output:
        cuda_version = "11.8"
        torch_cmd = "pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118"
    else:
        cuda_version = "Unknown"
        torch_cmd = "pip install torch torchvision torchaudio"
    
    print(f"Detected CUDA: {cuda_version}")
    print(f"\nRecommended PyTorch install command:")
    print(f"   {torch_cmd}")
    
except:
    print("Could not detect CUDA version automatically.")
    print("Please check nvidia-smi output manually.")

print("\n" + "=" * 70)
print("NEXT STEPS:")
print("=" * 70)
print("1. If PyTorch not installed or CUDA not available:")
print("   Run the recommended command above")
print("\n2. Then run: python setup_dependencies.py")
print("=" * 70)
