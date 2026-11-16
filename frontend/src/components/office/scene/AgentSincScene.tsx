"use client";

import { Html, OrbitControls } from "@react-three/drei";
import { useFrame, type ThreeEvent } from "@react-three/fiber";
import { useRef } from "react";
import * as THREE from "three";
import type { OfficeAgent } from "../types";

type Palette = {
  label: string;
  accent: string;
  secondary: string;
  floor: string;
  mark: string;
};

type SceneProps = {
  agents: OfficeAgent[];
  selectedAgentId: string | null;
  onSelectAgent: (id: string) => void;
  palette: Palette;
};

const roomLayout = [
  { id: "command", label: "COMMAND HUB", position: [0, -2.5] as [number, number], size: [4.2, 3.1] as [number, number], color: "#8B5CF6" },
  { id: "development", label: "DEVELOPMENT", position: [-4.6, -1.8] as [number, number], size: [4.1, 3.2] as [number, number], color: "#22D3EE" },
  { id: "design", label: "DESIGN STUDIO", position: [4.6, -1.8] as [number, number], size: [4.1, 3.2] as [number, number], color: "#FB7185" },
  { id: "research", label: "RESEARCH LIBRARY", position: [-4.6, 2.35] as [number, number], size: [4.1, 3.2] as [number, number], color: "#FBBF24" },
  { id: "quality", label: "QUALITY LAB", position: [4.6, 2.35] as [number, number], size: [4.1, 3.2] as [number, number], color: "#4ADE80" },
];

export function AgentSincScene({
  agents,
  selectedAgentId,
  onSelectAgent,
  palette,
}: SceneProps) {
  return (
    <>
      <color attach="background" args={["#080C17"]} />
      <ambientLight intensity={0.8} />
      <hemisphereLight args={["#DDEBFF", "#11182B", 1.1]} />
      <directionalLight
        castShadow
        position={[5, 12, 8]}
        intensity={2.3}
        shadow-mapSize-width={1024}
        shadow-mapSize-height={1024}
        shadow-camera-left={-12}
        shadow-camera-right={12}
        shadow-camera-top={12}
        shadow-camera-bottom={-12}
      />
      <pointLight position={[-7, 4, -5]} color={palette.accent} intensity={1.3} distance={18} />
      <pointLight position={[7, 3, 5]} color={palette.secondary} intensity={1.1} distance={16} />

      <OfficeFloor floorColor={palette.floor} />
      {roomLayout.map((room) => (
        <OfficeZone
          key={room.id}
          label={room.label}
          position={room.position}
          size={room.size}
          color={room.color}
        />
      ))}

      <CentralTable accent={palette.accent} />
      <ReceptionArch accent={palette.secondary} />

      {agents.map((agent) => (
        <AgentAvatar
          key={agent.id}
          agent={agent}
          selected={agent.id === selectedAgentId}
          onSelect={onSelectAgent}
        />
      ))}

      <OrbitControls
        makeDefault
        target={[0, 0.4, 0]}
        enableDamping
        dampingFactor={0.08}
        minDistance={10}
        maxDistance={27}
        minPolarAngle={0.45}
        maxPolarAngle={Math.PI / 2.12}
        maxAzimuthAngle={Math.PI / 1.6}
        minAzimuthAngle={-Math.PI / 1.6}
      />
    </>
  );
}

function OfficeFloor({ floorColor }: { floorColor: string }) {
  return (
    <group>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.08, 0]} receiveShadow>
        <planeGeometry args={[19, 14]} />
        <meshStandardMaterial color={floorColor} roughness={0.82} metalness={0.16} />
      </mesh>
      <gridHelper
        args={[19, 38, "#26344D", "#1A263C"]}
        position={[0, -0.065, 0]}
      />
      <mesh position={[0, -0.35, 0]}>
        <boxGeometry args={[19.2, 0.45, 14.2]} />
        <meshStandardMaterial color="#090E1A" roughness={0.72} />
      </mesh>
      <mesh position={[0, -0.1, -7.05]}>
        <boxGeometry args={[19.2, 0.55, 0.18]} />
        <meshStandardMaterial color="#1C2941" />
      </mesh>
      <mesh position={[0, -0.1, 7.05]}>
        <boxGeometry args={[19.2, 0.55, 0.18]} />
        <meshStandardMaterial color="#1C2941" />
      </mesh>
      <mesh position={[-9.55, -0.1, 0]}>
        <boxGeometry args={[0.18, 0.55, 14.2]} />
        <meshStandardMaterial color="#1C2941" />
      </mesh>
      <mesh position={[9.55, -0.1, 0]}>
        <boxGeometry args={[0.18, 0.55, 14.2]} />
        <meshStandardMaterial color="#1C2941" />
      </mesh>
    </group>
  );
}

function OfficeZone({
  label,
  position,
  size,
  color,
}: {
  label: string;
  position: [number, number];
  size: [number, number];
  color: string;
}) {
  const [x, z] = position;
  const [width, depth] = size;

  return (
    <group position={[x, 0, z]}>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.012, 0]} receiveShadow>
        <planeGeometry args={[width, depth]} />
        <meshStandardMaterial color={color} transparent opacity={0.12} roughness={0.9} />
      </mesh>
      <mesh position={[0, 0.055, -depth / 2]}>
        <boxGeometry args={[width, 0.09, 0.045]} />
        <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.28} />
      </mesh>
      <mesh position={[-width / 2, 0.055, 0]}>
        <boxGeometry args={[0.045, 0.09, depth]} />
        <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.18} />
      </mesh>
      <mesh position={[width / 2, 0.055, 0]}>
        <boxGeometry args={[0.045, 0.09, depth]} />
        <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.18} />
      </mesh>
      <Html position={[0, 1.95, -depth / 2 + 0.4]} center distanceFactor={11} style={{ pointerEvents: "none" }}>
        <div className="scene-zone-label" style={{ "--zone-color": color } as React.CSSProperties}>
          <i />
          {label}
        </div>
      </Html>
      <WorkDesk color={color} />
    </group>
  );
}

function WorkDesk({ color }: { color: string }) {
  return (
    <group position={[0, 0, 0.25]}>
      <mesh castShadow receiveShadow position={[0, 0.76, -0.3]}>
        <boxGeometry args={[1.5, 0.13, 0.75]} />
        <meshStandardMaterial color="#24334D" roughness={0.55} metalness={0.22} />
      </mesh>
      {[-0.62, 0.62].map((x) =>
        [-0.55, -0.05].map((z) => (
          <mesh key={`${x}-${z}`} castShadow position={[x, 0.37, z - 0.3]}>
            <boxGeometry args={[0.09, 0.72, 0.09]} />
            <meshStandardMaterial color="#576984" metalness={0.55} roughness={0.4} />
          </mesh>
        )),
      )}
      <mesh position={[0, 1.08, -0.5]} castShadow>
        <boxGeometry args={[0.82, 0.52, 0.07]} />
        <meshStandardMaterial color="#08111F" metalness={0.6} roughness={0.28} />
      </mesh>
      <mesh position={[0, 1.08, -0.455]}>
        <planeGeometry args={[0.72, 0.4]} />
        <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.45} />
      </mesh>
      <mesh position={[0, 0.85, -0.47]}>
        <boxGeometry args={[0.08, 0.12, 0.08]} />
        <meshStandardMaterial color="#71829B" metalness={0.5} />
      </mesh>
      <mesh position={[0, 0.2, 0.85]}>
        <cylinderGeometry args={[0.34, 0.34, 0.12, 18]} />
        <meshStandardMaterial color="#26334B" roughness={0.58} />
      </mesh>
      <mesh position={[0, 0.52, 0.85]}>
        <cylinderGeometry args={[0.07, 0.07, 0.58, 12]} />
        <meshStandardMaterial color="#465977" metalness={0.45} />
      </mesh>
    </group>
  );
}

function CentralTable({ accent }: { accent: string }) {
  return (
    <group position={[0, 0, 1.15]}>
      <mesh position={[0, 0.4, 0]} castShadow>
        <cylinderGeometry args={[1.05, 1.12, 0.28, 6]} />
        <meshStandardMaterial color="#1C2942" metalness={0.32} roughness={0.48} />
      </mesh>
      <mesh position={[0, 0.56, 0]}>
        <cylinderGeometry args={[0.78, 0.78, 0.04, 6]} />
        <meshStandardMaterial color={accent} emissive={accent} emissiveIntensity={0.4} />
      </mesh>
      <mesh position={[0, 0.17, 0]}>
        <cylinderGeometry args={[0.18, 0.3, 0.24, 6]} />
        <meshStandardMaterial color="#33435D" />
      </mesh>
      <Html position={[0, 1.25, 0]} center distanceFactor={11} style={{ pointerEvents: "none" }}>
        <div className="scene-center-label">SINC · OPERATIONS</div>
      </Html>
    </group>
  );
}

function ReceptionArch({ accent }: { accent: string }) {
  return (
    <group position={[0, 0, -5.3]}>
      <mesh position={[-1.55, 1.05, 0]}>
        <boxGeometry args={[0.13, 2.1, 0.16]} />
        <meshStandardMaterial color={accent} emissive={accent} emissiveIntensity={0.4} />
      </mesh>
      <mesh position={[1.55, 1.05, 0]}>
        <boxGeometry args={[0.13, 2.1, 0.16]} />
        <meshStandardMaterial color={accent} emissive={accent} emissiveIntensity={0.4} />
      </mesh>
      <mesh position={[0, 2.03, 0]}>
        <boxGeometry args={[3.25, 0.14, 0.16]} />
        <meshStandardMaterial color={accent} emissive={accent} emissiveIntensity={0.4} />
      </mesh>
      <Html position={[0, 2.55, 0]} center distanceFactor={10} style={{ pointerEvents: "none" }}>
        <div className="scene-reception-label">AGENTSINC HEADQUARTERS</div>
      </Html>
    </group>
  );
}

function AgentAvatar({
  agent,
  selected,
  onSelect,
}: {
  agent: OfficeAgent;
  selected: boolean;
  onSelect: (id: string) => void;
}) {
  const groupRef = useRef<THREE.Group>(null);

  useFrame(({ clock }) => {
    if (!groupRef.current) return;
    const bob = Math.sin(clock.elapsedTime * 2.2 + agent.position[0]) * 0.025;
    groupRef.current.position.y = bob;
    if (agent.status === "collaborating") {
      groupRef.current.rotation.y = Math.sin(clock.elapsedTime * 0.45) * 0.15;
    }
  });

  const handleSelect = (event: ThreeEvent<MouseEvent>) => {
    event.stopPropagation();
    onSelect(agent.id);
  };

  return (
    <group position={agent.position} onClick={handleSelect} ref={groupRef}>
      {selected ? (
        <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.08, 0]}>
          <torusGeometry args={[0.62, 0.045, 8, 36]} />
          <meshStandardMaterial color={agent.color} emissive={agent.color} emissiveIntensity={0.75} />
        </mesh>
      ) : null}
      <mesh castShadow position={[0, 0.93, 0]}>
        <cylinderGeometry args={[0.24, 0.32, 0.68, 12]} />
        <meshStandardMaterial color={agent.color} roughness={0.45} metalness={0.12} />
      </mesh>
      <mesh castShadow position={[0, 1.48, 0]}>
        <sphereGeometry args={[0.22, 18, 18]} />
        <meshStandardMaterial color="#E8D6C5" roughness={0.8} />
      </mesh>
      <mesh castShadow position={[-0.31, 0.94, 0]}>
        <capsuleFallback color={agent.color} />
      </mesh>
      <mesh castShadow position={[0.31, 0.94, 0]}>
        <capsuleFallback color={agent.color} />
      </mesh>
      <mesh castShadow position={[-0.13, 0.36, 0]}>
        <boxGeometry args={[0.12, 0.42, 0.16]} />
        <meshStandardMaterial color="#27334B" />
      </mesh>
      <mesh castShadow position={[0.13, 0.36, 0]}>
        <boxGeometry args={[0.12, 0.42, 0.16]} />
        <meshStandardMaterial color="#27334B" />
      </mesh>
      <Html position={[0, 1.95, 0]} center distanceFactor={10} style={{ pointerEvents: "none" }}>
        <div className={selected ? "scene-agent-tag selected" : "scene-agent-tag"} style={{ "--agent-color": agent.color } as React.CSSProperties}>
          <span>{agent.name}</span>
          <small>{agent.role}</small>
        </div>
      </Html>
    </group>
  );
}

function capsuleFallback({ color }: { color: string }) {
  return (
    <>
      <boxGeometry args={[0.13, 0.5, 0.13]} />
      <meshStandardMaterial color={color} roughness={0.5} />
    </>
  );
}
