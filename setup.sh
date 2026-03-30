#!/bin/bash

echo "🔧 Instalando dependencias del sistema..."

sudo apt update

sudo apt install -y \
build-essential \
pkg-config \
python3-dev \
libmariadb-dev \
libmariadb-dev-compat \
libcairo2-dev \
libfreetype6-dev

echo "✅ Dependencias listas"
