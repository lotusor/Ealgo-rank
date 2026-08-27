/**
 * PKCE（RFC 7636）工具 — 授权码 + PKCE 登录模式。
 *
 * 发起 passport 登录时生成 code_verifier（存 sessionStorage，回调页消费后清除），
 * 把 S256(code_verifier) 作为 code_challenge 传给护照；护照回调只回跳一次性
 * code（?code=...），回调页用 {code, code_verifier} 向护照
 * POST /api/v1/oauth/token/ 换取令牌——令牌不再经 URL fragment 下发。
 */

const VERIFIER_KEY = 'rank_oauth_pkce_verifier'

/** 生成 43-128 字符的随机 code_verifier（RFC 7636 §4.1 字符集）。 */
function randomVerifier(): string {
  const bytes = new Uint8Array(48) // 48 bytes -> 64 chars base64url
  crypto.getRandomValues(bytes)
  let bin = ''
  for (let i = 0; i < bytes.length; i++) bin += String.fromCharCode(bytes[i])
  return btoa(bin).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
}

/** BASE64URL(SHA256(verifier)) — S256 code challenge。 */
export async function s256Challenge(verifier: string): Promise<string> {
  const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(verifier))
  const bytes = new Uint8Array(digest)
  let bin = ''
  for (let i = 0; i < bytes.length; i++) bin += String.fromCharCode(bytes[i])
  return btoa(bin).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
}

/** 生成 PKCE 对：verifier 存 sessionStorage，返回 challenge。 */
export async function createPkcePair(): Promise<string> {
  const verifier = randomVerifier()
  sessionStorage.setItem(VERIFIER_KEY, verifier)
  return s256Challenge(verifier)
}

/** 取回 code_verifier 并清除存储（一次性）。无 verifier 时返回 null。 */
export function takeVerifier(): string | null {
  try {
    const v = sessionStorage.getItem(VERIFIER_KEY)
    sessionStorage.removeItem(VERIFIER_KEY)
    return v
  } catch {
    return null
  }
}
