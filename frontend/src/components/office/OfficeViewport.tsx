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
  focusedRoom: string;
};

export default function OfficeViewport({
  agents,
  selectedAgentId,
  onSelectAgent,
  theme,
  focusedRoom,
}: OfficeViewportProps) {
  const palette = BRAND_THEMES[theme];

  return (
    <Canvas
      shadows
      dpr={[1, 1.65]}
      camera={{ position: [15.5, 15, 18], fov: 38, near: 0.1, far: 120 }}
      gl={{
        antialias: true,
        alpha: false,
        powerPreference: "high-performance",
      }}
      onCreated={({ gl }) => {
        gl.setClearColor("#070B14", 1);
        gl.toneMappingExposure = 1.05;
      }}
    >
      <Suspense fallback={null}>
        <AgentSincScene
          agents={agents}
          selectedAgentId={selectedAgentId}
          onSelectAgent={onSelectAgent}
          palette={palette}
          focusedRoom={focusedRoom}
        />
      </Suspense>
    </Canvas>
  );
}
