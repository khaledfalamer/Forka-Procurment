// Forka Procurement Planner — settings for the GitHub version.
// SHEET_URL: the Google Apps Script web app URL (ends with /exec).
// ACCOUNTS_URL: the Forka Apps accounts server (public address). Used only to confirm it is the same person
//   before opening from the copy saved in this browser. Empty = skip that check.
// PIN: 'auto' = the PIN box appears only if the Sheet asks for one. true = always show it. false = never.
window.FORKA_CONFIG = {
  SHEET_URL: 'https://script.google.com/macros/s/AKfycbzaeb4OB4VNk_Pz8-IGNrnLdUNFLVtdeqUIgrFFZyl_Nl11f-anrlxJJ2OiZsaJDmN22w/exec',
  PIN: 'auto',
  ERP_URL: 'https://erp.forka.com/',
  ACCOUNTS_URL: 'https://forka-apps-443945615318.me-central1.run.app/accounts'
};
