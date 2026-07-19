import { useEffect, useMemo, useRef } from "react";

export interface RouteGenerationToken {
  routeKey: string | undefined;
  generation: number;
}

export interface RouteGeneration {
  capture(): RouteGenerationToken;
  isCurrent(token: RouteGenerationToken): boolean;
}

export function useRouteGeneration(routeKey: string | undefined): RouteGeneration {
  const state = useRef({ routeKey, generation: 0, mounted: false });

  if (state.current.routeKey !== routeKey) {
    state.current = {
      routeKey,
      generation: state.current.generation + 1,
      mounted: state.current.mounted,
    };
  }

  useEffect(() => {
    state.current.mounted = true;
    state.current.generation += 1;
    return () => {
      state.current.mounted = false;
      state.current.generation += 1;
    };
  }, [routeKey]);

  return useMemo(
    () => ({
      capture: () => ({ routeKey: state.current.routeKey, generation: state.current.generation }),
      isCurrent: (token: RouteGenerationToken) =>
        state.current.mounted &&
        token.routeKey === state.current.routeKey &&
        token.generation === state.current.generation,
    }),
    [],
  );
}
