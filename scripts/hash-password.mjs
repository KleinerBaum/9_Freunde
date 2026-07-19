import { pbkdf2Sync, randomBytes } from "node:crypto";

const password = process.argv[2];
if (!password || password.length < 12) {
  console.error("Usage: node scripts/hash-password.mjs <password-with-at-least-12-characters>");
  process.exit(1);
}

const salt = randomBytes(18).toString("base64url");
const hash = pbkdf2Sync(password, salt, 210_000, 32, "sha256").toString("base64url");
console.log(JSON.stringify({ password_salt: salt, password_hash: hash }, null, 2));
