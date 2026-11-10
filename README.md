# :package: apt

Serverless Debian/APT repository hosting custom `.deb` packages, served via GitHub Pages and built automatically with GitHub Actions.

Base URL: `https://nicholaswilde.io/apt`

---

## :wrench: Client Configuration

### 1. Add Repository Signing Key

Download ASCII-armored public key and store in keyring:

```bash
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://nicholaswilde.io/apt/public.key | sudo gpg --dearmor -o /etc/apt/keyrings/nicholaswilde-apt.gpg
sudo chmod a+r /etc/apt/keyrings/nicholaswilde-apt.gpg
```

### 2. Add APT Source List

```bash
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/nicholaswilde-apt.gpg] https://nicholaswilde.io/apt stable main" | sudo tee /etc/apt/sources.list.d/nicholaswilde-apt.list
```

### 3. Update & Install

```bash
sudo apt update
sudo apt install <package-name>
```

---

## :inbox_tray: Adding Packages

1. Place `.deb` package files in `pool/main/`:

   ```bash
   cp my-package_1.0.0_amd64.deb pool/main/
   ```

2. Commit and push:

   ```bash
   git add pool/main/my-package_1.0.0_amd64.deb
   git commit -m "feat(pkg): add my-package 1.0.0"
   git push origin main
   ```

3. GitHub Actions triggers automatically on changes under `pool/**/*.deb`, generates APT metadata (`Packages`, `Release`, `InRelease`), and deploys to GitHub Pages.

---

## :gear: Repository Secrets Setup

Configure GitHub repository secrets for package signing:

- `GPG_PRIVATE_KEY`: ASCII-armored private key export.
- `GPG_PASSPHRASE`: Passphrase for private key (empty if unprotected).

Trigger manual build/deploy:

```bash
rtk gh workflow run deploy-repo.yml | cat
```

---

## :balance_scale: License

[Apache License 2.0](LICENSE)

## :writing_hand: Author

​This project was started in 2026 by ​[Nicholas Wilde​](https://github.com/nicholaswilde)
