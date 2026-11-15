// Lo único de Node que usan los tests (leer un archivo del repo), declarado acá para no sumar
// @types/node al proyecto. Vitest corre en Node: el módulo existe aunque el front no lo use.
declare module 'node:fs' {
  export function readFileSync(ruta: string | URL, codificacion: 'utf8'): string
}
