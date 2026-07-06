"""
Shared password-derived AES-GCM encryption for the dashboard/landing pages.

Rather than hiding content behind a CSS overlay with a plaintext password
check (trivially bypassed via view-source or devtools), the actual page
content is encrypted at build time with a key derived from the password via
PBKDF2. The browser re-derives the same key from the entered password and
uses Web Crypto's AES-GCM to decrypt — wrong password means decryption
itself fails (GCM authentication), not just a hidden div.

All three pages (index.html and both dashboards) share the same SALT/
ITERATIONS/password, so the raw derived key is identical everywhere. The
browser caches that raw key in sessionStorage after first entry, so moving
between pages within one browser session doesn't re-prompt.

The password itself is never hardcoded here (that would defeat the point
the moment this file is committed) — it's read from the untracked
`.dashboard_password` file (see .gitignore) or the DASHBOARD_PASSWORD env
var, both local-only.
"""

import base64
import os
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

SALT_B64 = "Dzk43D55jZr2L5LbCKmYkw=="
ITERATIONS = 250000

_PASSWORD_FILE = os.path.join(os.path.dirname(__file__), ".dashboard_password")


def _default_password() -> str:
    env = os.environ.get("DASHBOARD_PASSWORD")
    if env:
        return env
    if os.path.exists(_PASSWORD_FILE):
        return open(_PASSWORD_FILE, encoding="utf-8").read().strip()
    raise RuntimeError(
        "No dashboard password found — set DASHBOARD_PASSWORD or create "
        f"{_PASSWORD_FILE} (gitignored) with the password as its only contents."
    )


def _derive_key(password: str | None = None) -> bytes:
    password = password or _default_password()
    salt = base64.b64decode(SALT_B64)
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=ITERATIONS)
    return kdf.derive(password.encode("utf-8"))


def encrypt(plaintext: str, password: str | None = None) -> tuple[str, str]:
    """Returns (iv_b64, ciphertext_b64) for the given plaintext string."""
    key = _derive_key(password)
    iv = os.urandom(12)
    ct = AESGCM(key).encrypt(iv, plaintext.encode("utf-8"), None)
    return base64.b64encode(iv).decode(), base64.b64encode(ct).decode()


# ── JS gate markup ────────────────────────────────────────────────────────

_GATE_STYLE = """
<style>
.pwgate{position:fixed;inset:0;z-index:9999;background:#1E3A5F;display:flex;align-items:center;justify-content:center;flex-direction:column;color:#fff;font-family:system-ui,-apple-system,sans-serif;padding:20px;text-align:center;}
.pwgate h2{font-size:1.3rem;margin-bottom:14px;}
.pwgate form{display:flex;gap:8px;flex-wrap:wrap;justify-content:center;}
.pwgate input{padding:10px 14px;border-radius:8px;border:none;font-size:1rem;min-width:200px;}
.pwgate button{padding:10px 18px;border-radius:8px;border:none;background:#7C3AED;color:#fff;font-weight:700;cursor:pointer;}
.pwgate .pwerr{color:#FCA5A5;margin-top:10px;font-size:.85rem;visibility:hidden;}
</style>
"""

_GATE_HTML = """
<div class="pwgate" id="pwgate">
  <h2>This dashboard is password protected</h2>
  <form id="pwform">
    <input id="pwinput" type="password" placeholder="Enter password" autofocus autocomplete="off" />
    <button type="submit">Enter</button>
  </form>
  <p class="pwerr" id="pwerror">Incorrect password</p>
</div>
<div id="app" style="display:none;"></div>
"""

_CRYPTO_JS_COMMON = """
const SALT_B64 = "%(salt)s";
const ITERATIONS = %(iterations)d;

function b64ToBytes(b64){ return Uint8Array.from(atob(b64), c => c.charCodeAt(0)); }
function bytesToB64(bytes){ return btoa(String.fromCharCode(...new Uint8Array(bytes))); }

async function deriveKeyFromPassword(password){
  const enc = new TextEncoder();
  const keyMaterial = await crypto.subtle.importKey('raw', enc.encode(password), {name:'PBKDF2'}, false, ['deriveKey']);
  return crypto.subtle.deriveKey(
    {name:'PBKDF2', salt: b64ToBytes(SALT_B64), iterations: ITERATIONS, hash:'SHA-256'},
    keyMaterial,
    {name:'AES-GCM', length:256},
    true,
    ['decrypt']
  );
}

async function importRawKey(rawB64){
  return crypto.subtle.importKey('raw', b64ToBytes(rawB64), {name:'AES-GCM'}, true, ['decrypt']);
}
"""


def dashboard_gate_html(body_content: str, password: str | None = None) -> str:
    """Encrypts body_content and returns the full gate+container+script markup
    to place right after <body>. Caller appends the encrypted payload in place
    of the real body, followed by </body></html>.
    """
    iv_b64, ct_b64 = encrypt(body_content, password)
    script = _CRYPTO_JS_COMMON % {"salt": SALT_B64, "iterations": ITERATIONS} + """
const IV_B64 = "%(iv)s";
const CT_B64 = "%(ct)s";

function revealContent(html){
  const app = document.getElementById('app');
  app.innerHTML = html;
  app.querySelectorAll('script').forEach(function(oldScript){
    const s = document.createElement('script');
    for (const attr of oldScript.attributes) s.setAttribute(attr.name, attr.value);
    s.textContent = oldScript.textContent;
    oldScript.replaceWith(s);
  });
  document.getElementById('pwgate').style.display = 'none';
  app.style.display = '';
}

async function tryReveal(key){
  const plainBuf = await crypto.subtle.decrypt({name:'AES-GCM', iv: b64ToBytes(IV_B64)}, key, b64ToBytes(CT_B64));
  revealContent(new TextDecoder().decode(plainBuf));
}

(async function(){
  const storedKey = sessionStorage.getItem('dashKey');
  if (storedKey) {
    try {
      await tryReveal(await importRawKey(storedKey));
      return;
    } catch (e) { sessionStorage.removeItem('dashKey'); }
  }
  document.getElementById('pwform').addEventListener('submit', async function(e){
    e.preventDefault();
    const errEl = document.getElementById('pwerror');
    errEl.style.visibility = 'hidden';
    try {
      const key = await deriveKeyFromPassword(document.getElementById('pwinput').value);
      await tryReveal(key);
      const raw = await crypto.subtle.exportKey('raw', key);
      sessionStorage.setItem('dashKey', bytesToB64(raw));
    } catch (err) {
      errEl.style.visibility = 'visible';
    }
  });
})();
""" % {"iv": iv_b64, "ct": ct_b64}
    return _GATE_STYLE + _GATE_HTML + "<script>\n" + script + "\n</script>\n"


def landing_gate_script() -> str:
    """For index.html: no real content to encrypt, so correctness is checked
    by attempting to decrypt a small verifier ciphertext. Navigation only
    happens after a verified key derivation, and the raw key is cached
    (sessionStorage) for the destination dashboard page to reuse.
    """
    verifier_iv_b64, verifier_ct_b64 = encrypt("ok")
    script = _CRYPTO_JS_COMMON % {"salt": SALT_B64, "iterations": ITERATIONS} + """
const VERIFIER_IV_B64 = "%(iv)s";
const VERIFIER_CT_B64 = "%(ct)s";

async function verifyKey(key){
  await crypto.subtle.decrypt({name:'AES-GCM', iv: b64ToBytes(VERIFIER_IV_B64)}, key, b64ToBytes(VERIFIER_CT_B64));
}

(function(){
  const overlay = document.getElementById('overlay');
  const form = document.getElementById('pwform');
  const input = document.getElementById('pwinput');
  const error = document.getElementById('pwerror');
  const cancel = document.getElementById('pwcancel');
  let target = null;

  document.querySelectorAll('.tile').forEach(function(tile){
    tile.addEventListener('click', function(){
      target = tile.getAttribute('data-href');
      error.style.visibility = 'hidden';
      input.value = '';
      overlay.classList.add('show');
      setTimeout(function(){ input.focus(); }, 50);
    });
  });

  cancel.addEventListener('click', function(){ overlay.classList.remove('show'); target = null; });
  overlay.addEventListener('click', function(e){ if (e.target === overlay) { overlay.classList.remove('show'); target = null; } });

  form.addEventListener('submit', async function(e){
    e.preventDefault();
    error.style.visibility = 'hidden';
    try {
      const key = await deriveKeyFromPassword(input.value);
      await verifyKey(key);
      const raw = await crypto.subtle.exportKey('raw', key);
      sessionStorage.setItem('dashKey', bytesToB64(raw));
      window.location.href = target;
    } catch (err) {
      error.style.visibility = 'visible';
    }
  });
})();
""" % {"iv": verifier_iv_b64, "ct": verifier_ct_b64}
    return script
