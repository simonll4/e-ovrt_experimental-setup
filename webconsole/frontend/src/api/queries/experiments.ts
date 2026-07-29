import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  deriveExperimentManifest, getControlCurrent, getCurrentExperiment, getDeriveDefaults,
  getExperiment, getExperimentAlerts, getExperimentManifests, getExperimentReport, runExperiment,
} from '..'
import { qk } from '../keys'
import { POLL } from '../queryClient'
import type {
  ControlCurrentSnapshot, DeriveDefaults, ExperimentAlert, ExperimentManifestSummary,
  ExperimentReport, ExperimentRunState,
} from '../../types'

export function useExperimentManifests() {
  return useQuery<ExperimentManifestSummary[]>({
    queryKey: qk.experiments.manifests,
    queryFn: getExperimentManifests,
    staleTime: 60_000,
  })
}

/** Experimento activo, o `null` si no hay ninguno (el BFF contesta 404 y el
 *  cliente ya lo traduce). Solo se repregunta mientras hay uno corriendo. */
export function useCurrentExperiment() {
  return useQuery<ExperimentRunState | null>({
    queryKey: qk.experiments.current,
    queryFn: getCurrentExperiment,
    refetchInterval: (query) =>
      query.state.data?.status === 'running' ? POLL.enCurso : false,
  })
}

export function useExperiment(id: string) {
  return useQuery<ExperimentRunState>({
    queryKey: qk.experiments.detail(id),
    queryFn: () => getExperiment(id),
    enabled: Boolean(id),
    refetchInterval: (query) => (query.state.data?.status === 'running' ? POLL.enCurso : false),
  })
}

export function useExperimentAlerts(id: string, enabled: boolean) {
  return useQuery<ExperimentAlert[]>({
    queryKey: qk.experiments.alerts(id),
    queryFn: () => getExperimentAlerts(id),
    enabled: enabled && Boolean(id),
  })
}

export function useExperimentReport(id: string, enabled: boolean) {
  return useQuery<ExperimentReport>({
    queryKey: qk.experiments.report(id),
    queryFn: () => getExperimentReport(id),
    enabled: enabled && Boolean(id),
    // El reporte se genera una vez y queda en disco.
    staleTime: Infinity,
  })
}

export function useDeriveDefaults(slug: string, enabled = true) {
  return useQuery<DeriveDefaults>({
    queryKey: qk.experiments.deriveDefaults(slug),
    queryFn: () => getDeriveDefaults(slug),
    enabled: enabled && Boolean(slug),
    staleTime: Infinity,
  })
}

/** Patrones de riesgo activos en el motor de reglas.
 *
 *  El control-plane no expone WS ni SSE (decisión suya: "polling, WS/SSE
 *  diferido"), así que esto se consulta por reloj — pero solo mientras hay algo
 *  vivo que mirar, que es lo que decide quien lo llama con `enabled`. */
export function useControlCurrent(enabled: boolean) {
  return useQuery<ControlCurrentSnapshot | null>({
    queryKey: qk.controlCurrent,
    queryFn: getControlCurrent,
    enabled,
    refetchInterval: enabled ? POLL.riesgoActivo : false,
  })
}

export function useRunExperiment() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (slug: string) => runExperiment({ slug }),
    onSuccess: () => {
      // Solo el experimento activo y el preflight: lanzar no cambia la lista de
      // manifiestos, y invalidarla entera forzaba una recarga inútil del
      // desplegable justo cuando el operador acaba de elegir qué correr.
      void qc.invalidateQueries({ queryKey: qk.experiments.current })
      void qc.invalidateQueries({ queryKey: qk.preflight })
    },
  })
}

export function useDeriveExperiment() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({
      slug,
      body,
    }: {
      slug: string
      body: { new_slug: string; changes?: string; overrides: Record<string, unknown> }
    }) => deriveExperimentManifest(slug, body),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: qk.experiments.manifests })
    },
  })
}
