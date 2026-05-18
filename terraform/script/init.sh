#!/bin/bash
apt-get update -y
apt-get install -y docker.io docker-compose-plugin git curl
systemctl start docker
systemctl enable docker