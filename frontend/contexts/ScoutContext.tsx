'use client';

import React, { createContext, useContext, useState } from 'react';

interface ScoutContextType {
  isLoading: boolean;
  setIsLoading: (value: boolean) => void;
}

const ScoutContext = createContext<ScoutContextType | undefined>(undefined);

export function ScoutProvider({ children }: { children: React.ReactNode }) {
  const [isLoading, setIsLoading] = useState(false);

  return (
    <ScoutContext.Provider value={{ isLoading, setIsLoading }}>
      {children}
    </ScoutContext.Provider>
  );
}

export function useScout() {
  const context = useContext(ScoutContext);
  if (!context) {
    throw new Error('useScout must be used within ScoutProvider');
  }
  return context;
}
