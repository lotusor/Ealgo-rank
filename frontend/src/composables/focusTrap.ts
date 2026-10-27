const FOCUSABLE = 'a[href], button, input, select, textarea, [tabindex]'

/** 弹窗内可 Tab 到的控件（排除禁用、不可见、显式 tabindex<0 的元素）。 */
export function getFocusable(root: HTMLElement | null | undefined): HTMLElement[] {
  if (!root) return []
  return Array.from(root.querySelectorAll<HTMLElement>(FOCUSABLE)).filter(
    (el) => el.tabIndex >= 0 && !el.hasAttribute('disabled') && el.getClientRects().length > 0,
  )
}

/** 焦点圈定的纯函数部分：越界时回环，焦点不在列表内时落到首/末。 */
export function nextFocusable(
  list: HTMLElement[],
  current: HTMLElement | null,
  shift: boolean,
): HTMLElement | null {
  if (!list.length) return null
  const index = current ? list.indexOf(current) : -1
  if (index < 0) return shift ? list[list.length - 1] : list[0]
  return list[(index + (shift ? -1 : 1) + list.length) % list.length]
}
