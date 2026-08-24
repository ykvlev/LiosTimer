# LiosTimer

Telegram bot for loot, wipe timers, clan subscriptions, and reminders.

## Requirements

- Python 3.11+
- Linux VPS or similar host
- GitHub repository
- Telegram bot token
- TON wallet address for payments

## Local setup

1. Create a virtual environment:
   ```bash
   python -m venv .venv
   . .venv/bin/activate
   pip install -r requirements.txt
   ```

2. Create `.env` from example:
   ```bash
   cp .env.example .env
   ```

3. Fill in values:
   ```env
   BOT_TOKEN=your_token_here
   ADMIN_ID=123456789
   TON_WALLET=UQBrsw7tct-MO8ZkSGsWUZtwH5LImu_Kmjad5kng1mho6RSt
   ```

4. Run the bot:
   ```bash
   python main.py
   ```

## Production deployment on VPS

The repo already contains a systemd service file and GitHub Actions deployment workflow.

### 1. Upload repository to GitHub

```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin <your-github-url>
git push -u origin main
```

### 2. Prepare VPS

```bash
sudo mkdir -p /opt/liostimer
sudo chown -R $USER:$USER /opt/liostimer
cd /opt/liostimer
git clone <your-github-url> .
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
nano .env
```

### 3. Add service

```bash
sudo cp liostimer.service /etc/systemd/system/liostimer.service
sudo systemctl daemon-reload
sudo systemctl enable liostimer
sudo systemctl start liostimer
sudo systemctl status liostimer --no-pager -l
```

Make sure `/opt/liostimer/.env` exists and contains valid values.

## GitHub Actions deployment

The workflow in `.github/workflows/deploy.yml` deploys to a VPS over SSH on each push to `main`.

Required GitHub repository secrets:

- `VPS_HOST`
- `VPS_USER`
- `VPS_SSH_KEY`

The deploy script runs:

```bash
cd /opt/liostimer
git pull origin main
.venv/bin/pip install -r requirements.txt -q
systemctl restart liostimer
```

## Notes

- Keep the `.env` file on the server only; do not commit it.
- The database file is created under `data/bot.db`.
- If the bot is being used in production, add monitoring and log rotation.
