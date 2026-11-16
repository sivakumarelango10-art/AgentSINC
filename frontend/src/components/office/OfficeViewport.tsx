"use client";

import { Canvas } from "@react-three/fiber";
import { Suspense } from "react";
import { AgentSincScene } from "./scene/AgentSincScene";
import { BRAND_THEMES, type BrandTheme, type OfficeAgent } from "./types";

type OfficeViewportProps = {
  agents: OfficeAgent[];
  selectedAgentId: string | null;
  onSelectAgent: (id: string) => void;
  theme: BrandTheme;
};

export default function OfficeViewport({
  agents,
  selectedAgentId,
  onSelectAgent,
  theme,
}: OfficeViewportProps) {
  const palette = BRAND_THEMES[theme];

  return (
    <Canvas
      shadows
      dpr={[1, 1.5]}
      camera={{ position: [13, 13, 16], fov: 42, near: 0.1, far: 100 }}
      gl={{
        antialias: true,
        alpha: false,
        powerPreference: "high-performance",
      }}
      onCreated={({ gl }) => {
        gl.setClearColor("#080C17", 1);
      }}
    >
      <Suspense fallback={null}>
        <AgentSincScene
          agents={agents}
          selectedAgentId={selectedAgentId}
          onSelectAgent={onSelectAgent}
          palette={palette}
        />
      </Suspense>
    </Canvas>
  );
}
