#!/bin/bash
# Start frontend dev server (port 5173)
cd "$(dirname "$0")/../frontend"
npm install --silent && npm run dev
