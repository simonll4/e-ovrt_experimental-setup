import { CONDITION_NAMES } from '../../labels'
import NombreCodigo from './NombreCodigo'

/** Una condición de riesgo: el nombre llano y el código al lado (plan §4.2). */
export default function ConditionName({ code }: { code: string }) {
  return <NombreCodigo codigo={code} nombre={CONDITION_NAMES[code]} />
}
