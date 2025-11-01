// capacior.config.ts
import { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'app.kd.classmint', 
  appName: 'ClassMint',
  webDir: 'dist',
  bundledWebRuntime: false,
  server: {
    androidScheme: 'http'
  },
  android: {
    allowMixedContent: true,
    captureInput: true,
    webContentsDebuggingEnabled: true
  }
};

export default config;