// Password rules for new accounts. Mirrored server-side in
// backend/services/paid_signup.py (password_problem) for the paid signup flow.
export const PASSWORD_MIN_LENGTH = 8;

export const PASSWORD_RULES = [
  { id: "length", label: `${PASSWORD_MIN_LENGTH}+ characters`, test: (p) => p.length >= PASSWORD_MIN_LENGTH },
  { id: "upper", label: "Uppercase letter", test: (p) => /[A-Z]/.test(p) },
  { id: "lower", label: "Lowercase letter", test: (p) => /[a-z]/.test(p) },
  { id: "number", label: "Number", test: (p) => /[0-9]/.test(p) },
  { id: "special", label: "Symbol (!@#$…)", test: (p) => /[^A-Za-z0-9]/.test(p) },
];

/** True when every rule passes. */
export function passwordOk(password) {
  return PASSWORD_RULES.every((r) => r.test(password || ""));
}
