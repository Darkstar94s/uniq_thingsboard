/**
 * UNIQ SMART HOME - Platform Configuration & Feature Toggles
 * Centralized control for UNIQ brand features, menu curation, and protocol settings.
 */

export interface UniqConfig {
  brandName: string;
  smartHomeMode: boolean;
  customerMenu: {
    hideEdgeInstances: boolean;
    hideEntityViews: boolean;
    directSmartDevices: boolean;
  };
  supportedProtocols: {
    wifi: boolean;
    zigbee: boolean;
    matter: boolean;
    ble: boolean;
  };
}

export const UNIQ_CONFIG: UniqConfig = {
  brandName: 'UNIQ',
  smartHomeMode: true,
  customerMenu: {
    hideEdgeInstances: true,
    hideEntityViews: true,
    directSmartDevices: true,
  },
  supportedProtocols: {
    wifi: true,
    zigbee: true,
    matter: true,
    ble: false,
  }
};
