#!/bin/bash
# Build script for custom vLLM ROCm 7.2.1 container
# E:\AI-Setup\build_vllm_rocm.sh

set -e

IMAGE_NAME="wsl-vllm-rocm72"
CONTAINER_NAME="wsl-vllm-build"

echo "=== Building custom vLLM ROCm 7.2.1 container ==="

# Stop and remove any existing build container
echo "Cleaning up any existing build container..."
docker stop $CONTAINER_NAME 2>/dev/null || true
docker rm $CONTAINER_NAME 2>/dev/null || true

# Create working directory for build context
BUILD_DIR="/tmp/vllm_build_$$"
mkdir -p $BUILD_DIR
cp "$(dirname "$0")/Dockerfile.vllm-rocm72" "$BUILD_DIR/"

echo "Build context: $BUILD_DIR"

# Build the image
docker build -t $IMAGE_NAME -f "$BUILD_DIR/Dockerfile.vllm-rocm72" "$BUILD_DIR"

# Cleanup
rm -rf $BUILD_DIR

echo "=== Build complete ==="
echo "Image: $IMAGE_NAME"
echo ""
echo "To run: docker run --rm --device=/dev/dxg -v /usr/lib/wsl/lib:/usr/lib/wsl/lib -p 8000:8000 $IMAGE_NAME"
