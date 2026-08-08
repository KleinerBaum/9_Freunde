import { pbkdf2Sync, randomBytes } from "node:crypto";

const password = process.argv[2];
if (!password || password.length < 12) {
  console.error("Usage: node scripts/hash-password.mjs <password-with-at-least-12-characters>");
  process.exit(1);
}

const salt = randomBytes(18).toString("base64url");
const iterations = 210_000;
const digest = pbkdf2Sync(password, salt, iterations, 32, "sha256")
  .toString("base64url");
const hash = `pbkdf2-sha256$${iterations}$${digest}`;
console.log(JSON.stringify({ password_salt: salt, password_hash: hash }, null, 2));
