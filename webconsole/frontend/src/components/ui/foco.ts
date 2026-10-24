/** Enfoca el primer elemento que coincide con `selector` apenas exista: la
 *  vista nueva puede tardar un render en montarlo. Para cuando el control que
 *  abrió o cerró una vista desaparece con ella — sin esto el foco cae al
 *  documento y el lector de pantalla pierde el lugar. Los títulos reciben
 *  `tabindex="-1"` para poder enfocarse sin entrar en el orden de Tab. */
export function enfocarCuandoAparezca(selector: string) {
  let intentos = 0
  const intentar = () => {
    const el = document.querySelector<HTMLElement>(selector)
    if (el) {
      if (/^H[1-6]$/.test(el.tagName) && !el.hasAttribute('tabindex')) el.setAttribute('tabindex', '-1')
      el.focus()
      return
    }
    if (intentos++ < 20) window.setTimeout(intentar, 50)
  }
  window.setTimeout(intentar, 0)
}
