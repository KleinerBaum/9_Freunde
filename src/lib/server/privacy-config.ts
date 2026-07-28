const value = (name: string) => process.env[name]?.trim() || "";

export function privacyConfiguration() {
  return {
    controllerName: value("PRIVACY_CONTROLLER_NAME"),
    controllerAddress: value("PRIVACY_CONTROLLER_ADDRESS"),
    privacyEmail: value("PRIVACY_CONTACT_EMAIL"),
    dpoEmail: value("PRIVACY_DPO_EMAIL"),
    legalRepresentative: value("LEGAL_REPRESENTATIVE"),
    legalRegister: value("LEGAL_REGISTER"),
    supervisoryAuthority: value("LEGAL_SUPERVISORY_AUTHORITY")
  };
}

export function privacyConfigurationReady(): boolean {
  return Object.values(privacyConfiguration()).every(Boolean);
}
