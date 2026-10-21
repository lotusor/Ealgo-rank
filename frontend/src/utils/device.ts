// 稳定设备标识：每个浏览器生成一次并持久化，用于后端设备指纹限流。
// 校园网/企业网共享 NAT 出口 IP 场景下，设备指纹可在同一出口 IP 下区分不同浏览器，
// 让登录/登出限流精准落到「具体设备」而非「整片 IP」，避免误伤或绕过。
const DEVICE_ID_KEY = 'ealgo_device_id'

export function getDeviceId(): string {
  let id = localStorage.getItem(DEVICE_ID_KEY)
  if (!id) {
    id =
      typeof crypto !== 'undefined' && 'randomUUID' in crypto
        ? crypto.randomUUID()
        : `d_${Date.now().toString(16)}_${Math.random().toString(16).slice(2)}`
    localStorage.setItem(DEVICE_ID_KEY, id)
  }
  return id
}
