# 🎯 ClassMint Student App

A mobile application built with Ionic + Vue 3 + Capacitor, demonstrating a complete flow of "Scan QR Code + Balance Display + Account Login".

## ✨ Features

- 🔐 **Account Login**: Local validation (student/123456)
- 📱 **Scan & Claim**: Support for DEMO-100 / DEMO-500 tokens
- 💰 **Balance Management**: Real-time balance display and recent 10 transactions
- 🔗 **Deep Linking**: Support for `/claim?token=...` direct claim
- 📱 **Responsive Design**: Perfect adaptation for mobile and desktop
- 💾 **Local Storage**: Using localStorage to simulate database

## 🚀 Quick Start

### Requirements

- Node.js 16+
- npm or yarn
- Android Studio (for Android builds)

### Install Dependencies

```bash
npm install
```

### Development Mode

```bash
npm run dev
```

### Build Android Application

```bash
npm i -D @capacitor/cli
npm i @capacitor/core @capacitor/android
npx cap add android
npm run build
npx cap sync android
npx cap open android
```
For updates only:
```bash
npm run build
npx cap sync android
npx cap open android
```

## 📱 Page Navigation

| Path | Page | Function |
|------|------|----------|
| `/` | Home | Welcome page, display current status |
| `/login` | Login | Account login |
| `/scan` | Scan | QR code scanning for rewards |
| `/me` | Account | Balance and transaction history |
| `/claim` | Deep Link | Handle claim?token=... |

## 🧪 Demo Flow

1. **Login**: Visit `/login`, use `student/123456` to login
2. **Scan**: After successful login, navigate to `/scan`, click "Start Scanning"
3. **Claim Reward**: Scan QR code containing token
4. **Check Balance**: Visit `/me` to view balance increase and transaction history

## 🏗️ Project Structure

```
src/
├── views/                 # Page components
│   ├── HomePage.vue      # Home page
│   ├── LoginView.vue     # Login page
│   ├── ScanView.vue      # Scan page
│   ├── MeView.vue        # Account page
│   └── ClaimDeepLinkView.vue # Deep link page
├── store/                # State management
│   └── user.ts          # User state
├── api/                  # API interfaces
│   └── mockApi.ts       # Mock API
├── mock/                 # Mock data
│   └── db.ts            # Local database
└── router/               # Router configuration
    └── index.ts         # Route definitions
```

## 🔧 Tech Stack

- **Frontend Framework**: Vue 3 + Composition API
- **UI Component Library**: Ionic Vue 8
- **State Management**: Pinia
- **Routing**: Vue Router 4
- **Build Tool**: Vite
- **Mobile**: Capacitor 7
- **QR Code Scanning**: @capacitor-mlkit/barcode-scanning

## 📋 Acceptance Criteria

- ✅ Login successfully and enter scan page
- ✅ Balance +5.00 after scanning DEMO-500
- ✅ Shows "Token already used" on second scan
- ✅ "My Account" shows recent transactions with correct timestamps
- ✅ No blank pages, main flow without errors

## 🐛 Common Issues

### PowerShell Execution Policy Restriction

If you encounter `npm run dev` execution failure, please:

```powershell
# Run PowerShell as Administrator
Set-ExecutionPolicy RemoteSigned

# Or temporarily bypass
Set-ExecutionPolicy Bypass -Scope Process
```

### QR Code Permission Issues

First-time use of the scanning feature requires camera permission, please ensure:

1. Allow camera permission in browser
2. Grant camera permission to the app on mobile devices

## 📄 License

MIT License

## 🤝 Contributing

Issues and Pull Requests are welcome!
