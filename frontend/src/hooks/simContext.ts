import { createContext, useContext } from 'react';
import { useSimulation } from './useSimulation';

type SimApi = ReturnType<typeof useSimulation>;

export const SimContext = createContext<SimApi | null>(null);

export function useSim(): SimApi {
  const ctx = useContext(SimContext);
  if (!ctx) throw new Error('Simulation context missing');
  return ctx;
}
