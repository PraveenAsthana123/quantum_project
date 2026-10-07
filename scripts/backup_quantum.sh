#!/bin/bash
# Backup quantum portal DB and results. Safe to run repeatedly.
set -e
BACKUP_DIR="/mnt/deepa/quantum/.backups/$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"

echo "Backing up to $BACKUP_DIR..."

# DB
cp /mnt/deepa/quantum/api/quantum_portal.db "$BACKUP_DIR/quantum_portal.db" 2>/dev/null && echo "✓ DB backed up"

# Results JSONs
for lab in qc-banking-lab qc-finance-lab qc-healthcare-lab qc-logistics-lab qc-security-lab qc-cryptography-module; do
  mkdir -p "$BACKUP_DIR/$lab"
  cp -r /mnt/deepa/quantum/$lab/results/ "$BACKUP_DIR/$lab/" 2>/dev/null || true
  cp -r /mnt/deepa/quantum/$lab/data/ "$BACKUP_DIR/$lab/" 2>/dev/null || true
done

echo "✓ Backup complete: $BACKUP_DIR"
du -sh "$BACKUP_DIR"

# Keep only last 7 backups
ls -dt /mnt/deepa/quantum/.backups/*/ 2>/dev/null | tail -n +8 | xargs rm -rf 2>/dev/null || true
echo "✓ Old backups pruned (keeping 7)"
