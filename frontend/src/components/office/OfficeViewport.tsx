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
  followSelectedAgent: boolean;
  focusRequest: number;
};

export default function OfficeViewport({
  agents,
  selectedAgentId,
  onSelectAgent,
  theme,
  focusedRoom,
  followSelectedAgent,
  focusRequest,
}: OfficeViewportProps) {
  const palette = BRAND_THEMES[theme];

  return (
    <Canvas
      shadows
      dpr={[1, 1.5]}
      camera={{ position: [16, 11.5, 20], fov: 37, near: 0.1, far: 140 }}
      gl={{
        antialias: true,
        alpha: false,
        powerPreference: "high-performance",
      }}
      onCreated={({ gl }) => {
        gl.setClearColor("#EAF0F6", 1);
        gl.toneMappingExposure = 1.18;
      }}
    >
      <Suspense fallback={null}>
        <AgentSincScene
          agents={agents}
          selectedAgentId={selectedAgentId}
          onSelectAgent={onSelectAgent}
          palette={palette}
          focusedRoom={focusedRoom}
          followSelectedAgent={followSelectedAgent}
          focusRequest={focusRequest}
        />
      </Suspense>
    </Canvas>
  );
}
