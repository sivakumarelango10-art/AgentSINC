"use client";

import { Html, OrbitControls } from "@react-three/drei";
import { useFrame, type ThreeEvent } from "@react-three/fiber";
import { useMemo, useRef } from "react";
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
  focusedRoom: string;
};

const roomLayout = [
  { id: "command", label: "COMMAND HUB", position: [0, -4.5] as [number, number], size: [5.6, 3.8] as [number, number], color: "#8B5CF6" },
  { id: "development", label: "DEVELOPMENT STUDIO", position: [-6.3, -0.9] as [number, number], size: [5.1, 3.8] as [number, number], color: "#22D3EE" },
  { id: "design", label: "DESIGN STUDIO", position: [6.3, -0.9] as [number, number], size: [5.1, 3.8] as [number, number], color: "#FB7185" },
  { id: "research", label: "RESEARCH LIBRARY", position: [-6.3, 4.25] as [number, number], size: [5.1, 3.8] as [number, number], color: "#FBBF24" },
  { id: "quality", label: "QUALITY LAB", position: [6.3, 4.25] as [number, number], size: [5.1, 3.8] as [number, number], color: "#4ADE80" },
];

const roomTargets: Record<string, [number, number, number]> = {
  all: [0, 0.55, 0],
  command: [0, 0.65, -4.5],
  development: [-6.3, 0.55, -0.9],
  design: [6.3, 0.55, -0.9],
  research: [-6.3, 0.55, 4.25],
  quality: [6.3, 0.55, 4.25],
};

export function AgentSincScene({
  agents,
  selectedAgentId,
  onSelectAgent,
  palette,
  focusedRoom,
}: SceneProps) {
  const roomTarget = roomTargets[focusedRoom] ?? roomTargets.all;

  return (
    <>
      <color attach="background" args={["#070B14"]} />
      <fog attach="fog" args={["#070B14", 21, 48]} />
      <ambientLight intensity={0.55} />
      <hemisphereLight args={["#DDEBFF", "#11182B", 1.15]} />
      <directionalLight
        castShadow
        position={[6, 16, 9]}
        intensity={2.2}
        shadow-mapSize-width={2048}
        shadow-mapSize-height={2048}
        shadow-camera-left={-18}
        shadow-camera-right={18}
        shadow-camera-top={18}
        shadow-camera-bottom={-18}
        shadow-bias={-0.00015}
      />
      <pointLight position={[-8, 5, -6]} color={palette.accent} intensity={1.7} distance={24} />
      <pointLight position={[8, 5, 7]} color={palette.secondary} intensity={1.55} distance={22} />
      <pointLight position={[0, 5, -5]} color="#8B5CF6" intensity={1.2} distance={17} />

      <OfficeFloor floorColor={palette.floor} accent={palette.accent} />
      {roomLayout.map((room) => (
        <OfficeZone
          key={room.id}
          label={room.label}
          position={room.position}
          size={room.size}
          color={room.color}
          focused={focusedRoom === room.id}
        />
      ))}

      <CentralCommandHub accent={palette.accent} secondary={palette.secondary} />
      <GlassMeetingRoom accent={palette.secondary} />
      <ReceptionArch accent={palette.secondary} />
      <Plant position={[-10, 0, -6.8]} />
      <Plant position={[10, 0, -6.8]} />
      <Plant position={[-10, 0, 7.2]} />
      <Plant position={[10, 0, 7.2]} />
      <DisplayWall position={[0, 0, -8.15]} accent={palette.accent} />

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
        target={roomTarget}
        enableDamping
        dampingFactor={0.075}
        minDistance={8}
        maxDistance={33}
        minPolarAngle={0.38}
        maxPolarAngle={Math.PI / 2.08}
        minAzimuthAngle={-Math.PI / 1.45}
        maxAzimuthAngle={Math.PI / 1.45}
        screenSpacePanning={false}
      />
    </>
  );
}

function OfficeFloor({ floorColor, accent }: { floorColor: string; accent: string }) {
  return (
    <group>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.12, 0]} receiveShadow>
        <planeGeometry args={[26, 20]} />
        <meshStandardMaterial color={floorColor} roughness={0.76} metalness={0.22} />
      </mesh>
      <gridHelper args={[26, 52, "#34445F", "#1A2940"]} position={[0, -0.105, 0]} />
      <mesh position={[0, -0.42, 0]}>
        <boxGeometry args={[26.2, 0.55, 20.2]} />
        <meshStandardMaterial color="#080E1B" roughness={0.64} metalness={0.22} />
      </mesh>
      <mesh position={[0, -0.12, -10]}>
        <boxGeometry args={[26.2, 0.7, 0.18]} />
        <meshStandardMaterial color="#263852" metalness={0.42} />
      </mesh>
      <mesh position={[0, -0.12, 10]}>
        <boxGeometry args={[26.2, 0.7, 0.18]} />
        <meshStandardMaterial color="#263852" metalness={0.42} />
      </mesh>
      <mesh position={[-13, -0.12, 0]}>
        <boxGeometry args={[0.18, 0.7, 20.2]} />
        <meshStandardMaterial color="#263852" metalness={0.42} />
      </mesh>
      <mesh position={[13, -0.12, 0]}>
        <boxGeometry args={[0.18, 0.7, 20.2]} />
        <meshStandardMaterial color="#263852" metalness={0.42} />
      </mesh>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.085, 0]}>
        <planeGeometry args={[25.4, 19.4]} />
        <meshBasicMaterial color={accent} transparent opacity={0.018} />
      </mesh>
    </group>
  );
}

function OfficeZone({
  label,
  position,
  size,
  color,
  focused,
}: {
  label: string;
  position: [number, number];
  size: [number, number];
  color: string;
  focused: boolean;
}) {
  const [x, z] = position;
  const [width, depth] = size;
  const opacity = focused ? 0.19 : 0.105;

  return (
    <group position={[x, 0, z]}>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.015, 0]} receiveShadow>
        <planeGeometry args={[width, depth]} />
        <meshStandardMaterial color={color} transparent opacity={opacity} roughness={0.9} />
      </mesh>
      <mesh position={[0, 0.06, -depth / 2]}>
        <boxGeometry args={[width, 0.12, 0.06]} />
        <meshStandardMaterial color={color} emissive={color} emissiveIntensity={focused ? 0.72 : 0.35} />
      </mesh>
      <mesh position={[-width / 2, 0.06, 0]}>
        <boxGeometry args={[0.06, 0.12, depth]} />
        <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.3} />
      </mesh>
      <mesh position={[width / 2, 0.06, 0]}>
        <boxGeometry args={[0.06, 0.12, depth]} />
        <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.3} />
      </mesh>
      <GlassDivider color={color} width={width} depth={depth} />
      <Html position={[0, 2.45, -depth / 2 + 0.45]} center distanceFactor={11} style={{ pointerEvents: "none" }}>
        <div className={focused ? "scene-zone-label focused" : "scene-zone-label"} style={{ "--zone-color": color } as React.CSSProperties}>
          <i />{label}
        </div>
      </Html>
      <WorkDesk color={color} />
      {label.includes("RESEARCH") ? <BookShelf position={[-1.75, 0, -0.2]} /> : null}
      {label.includes("QUALITY") ? <TestBench position={[1.65, 0, -0.2]} color={color} /> : null}
      {label.includes("DESIGN") ? <MoodWall position={[1.6, 0, -1.2]} color={color} /> : null}
    </group>
  );
}

function GlassDivider({ color, width, depth }: { color: string; width: number; depth: number }) {
  return (
    <group>
      <mesh position={[0, 1.05, -depth / 2 + 0.08]}>
        <boxGeometry args={[width - 0.25, 1.8, 0.055]} />
        <meshPhysicalMaterial color="#9CB4D4" transparent opacity={0.08} roughness={0.13} metalness={0.3} />
      </mesh>
      <mesh position={[-width / 2 + 0.08, 0.95, 0]}>
        <boxGeometry args={[0.055, 1.65, depth - 0.2]} />
        <meshPhysicalMaterial color="#9CB4D4" transparent opacity={0.07} roughness={0.14} metalness={0.25} />
      </mesh>
      <mesh position={[width / 2 - 0.08, 0.95, 0]}>
        <boxGeometry args={[0.055, 1.65, depth - 0.2]} />
        <meshPhysicalMaterial color="#9CB4D4" transparent opacity={0.07} roughness={0.14} metalness={0.25} />
      </mesh>
      <mesh position={[0, 2, -depth / 2 + 0.04]}>
        <boxGeometry args={[width, 0.035, 0.07]} />
        <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.55} />
      </mesh>
    </group>
  );
}

function WorkDesk({ color }: { color: string }) {
  return (
    <group position={[0, 0, 0.2]}>
      <mesh castShadow receiveShadow position={[0, 0.78, -0.35]}>
        <boxGeometry args={[1.9, 0.16, 0.9]} />
        <meshStandardMaterial color="#2A3954" roughness={0.42} metalness={0.3} />
      </mesh>
      <mesh position={[0, 0.69, -0.35]}>
        <boxGeometry args={[1.55, 0.035, 0.72]} />
        <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.17} />
      </mesh>
      {[-0.78, 0.78].map((x) => [-0.7, -0.02].map((z) => (
        <mesh key={`${x}-${z}`} castShadow position={[x, 0.39, z - 0.35]}>
          <boxGeometry args={[0.095, 0.74, 0.095]} />
          <meshStandardMaterial color="#667A98" metalness={0.62} roughness={0.33} />
        </mesh>
      )))}
      <mesh position={[0, 1.2, -0.65]} castShadow>
        <boxGeometry args={[1.05, 0.66, 0.09]} />
        <meshStandardMaterial color="#07111F" metalness={0.72} roughness={0.22} />
      </mesh>
      <mesh position={[0, 1.2, -0.6]}>
        <planeGeometry args={[0.9, 0.52]} />
        <meshBasicMaterial color={color} />
      </mesh>
      <mesh position={[0, 0.87, -0.59]}>
        <boxGeometry args={[0.1, 0.13, 0.11]} />
        <meshStandardMaterial color="#8395B1" metalness={0.6} />
      </mesh>
      <OfficeChair color={color} position={[0, 0, 1.05]} />
      <DeskLamp color={color} position={[-0.72, 0.88, -0.28]} />
    </group>
  );
}

function OfficeChair({ color, position }: { color: string; position: [number, number, number] }) {
  return (
    <group position={position}>
      <mesh position={[0, 0.57, 0]}>
        <boxGeometry args={[0.68, 0.13, 0.64]} />
        <meshStandardMaterial color="#263653" roughness={0.55} />
      </mesh>
      <mesh position={[0, 1.03, -0.25]}>
        <boxGeometry args={[0.68, 0.88, 0.13]} />
        <meshStandardMaterial color="#334663" roughness={0.52} />
      </mesh>
      <mesh position={[0, 0.29, 0]}>
        <cylinderGeometry args={[0.055, 0.055, 0.52, 10]} />
        <meshStandardMaterial color="#7586A2" metalness={0.65} />
      </mesh>
      <mesh position={[0, 0.025, 0]}>
        <cylinderGeometry args={[0.34, 0.34, 0.07, 16]} />
        <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.12} />
      </mesh>
    </group>
  );
}

function DeskLamp({ color, position }: { color: string; position: [number, number, number] }) {
  return (
    <group position={position}>
      <mesh position={[0, 0.13, 0]}>
        <cylinderGeometry args={[0.12, 0.12, 0.055, 12]} />
        <meshStandardMaterial color="#64748B" metalness={0.7} />
      </mesh>
      <mesh position={[0.02, 0.35, 0]} rotation={[0, 0, -0.22]}>
        <cylinderGeometry args={[0.025, 0.03, 0.4, 8]} />
        <meshStandardMaterial color="#8191AA" metalness={0.65} />
      </mesh>
      <mesh position={[0.08, 0.56, 0]}>
        <coneGeometry args={[0.18, 0.22, 12]} />
        <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.42} />
      </mesh>
    </group>
  );
}

function CentralCommandHub({ accent, secondary }: { accent: string; secondary: string }) {
  return (
    <group position={[0, 0, 0]}>
      <mesh position={[0, 0.2, 0]} castShadow>
        <cylinderGeometry args={[2.3, 2.5, 0.3, 8]} />
        <meshStandardMaterial color="#1B2940" metalness={0.42} roughness={0.35} />
      </mesh>
      <mesh position={[0, 0.37, 0]}>
        <cylinderGeometry args={[1.8, 1.8, 0.045, 8]} />
        <meshStandardMaterial color={accent} emissive={accent} emissiveIntensity={0.45} />
      </mesh>
      <mesh position={[0, 0.57, 0]}>
        <cylinderGeometry args={[1.15, 1.15, 0.17, 8]} />
        <meshStandardMaterial color="#263956" metalness={0.3} roughness={0.36} />
      </mesh>
      <mesh position={[0, 0.72, 0]}>
        <cylinderGeometry args={[0.83, 0.83, 0.045, 8]} />
        <meshStandardMaterial color={secondary} emissive={secondary} emissiveIntensity={0.58} />
      </mesh>
      <mesh position={[0, 0.86, 0]}>
        <octahedronGeometry args={[0.34, 0]} />
        <meshStandardMaterial color="#E5F7FF" emissive={accent} emissiveIntensity={0.7} metalness={0.35} roughness={0.18} />
      </mesh>
      <Html position={[0, 1.45, 0]} center distanceFactor={12} style={{ pointerEvents: "none" }}>
        <div className="scene-center-label">SINC · COMMAND CORE</div>
      </Html>
    </group>
  );
}

function GlassMeetingRoom({ accent }: { accent: string }) {
  return (
    <group position={[0, 0, 4.15]}>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.02, 0]}>
        <planeGeometry args={[4.3, 2.1]} />
        <meshStandardMaterial color="#60738F" transparent opacity={0.15} />
      </mesh>
      {[-2.12, 2.12].map((x) => (
        <mesh key={x} position={[x, 1.0, 0]}>
          <boxGeometry args={[0.06, 1.9, 2.1]} />
          <meshPhysicalMaterial color="#B9D9F6" transparent opacity={0.12} roughness={0.1} />
        </mesh>
      ))}
      <mesh position={[0, 0.08, -1.02]}>
        <boxGeometry args={[4.2, 0.08, 0.07]} />
        <meshStandardMaterial color={accent} emissive={accent} emissiveIntensity={0.4} />
      </mesh>
      <mesh position={[0, 0.48, 0]}>
        <cylinderGeometry args={[0.78, 0.86, 0.16, 8]} />
        <meshStandardMaterial color="#34435F" metalness={0.3} />
      </mesh>
      {[-1.35, 1.35].map((x) => (
        <mesh key={x} position={[x, 0.32, 0]}>
          <cylinderGeometry args={[0.24, 0.24, 0.55, 10]} />
          <meshStandardMaterial color="#34435F" />
        </mesh>
      ))}
      <Html position={[0, 2.15, -1.1]} center distanceFactor={12} style={{ pointerEvents: "none" }}>
        <div className="scene-room-sign">COLLABORATION LOUNGE</div>
      </Html>
    </group>
  );
}

function ReceptionArch({ accent }: { accent: string }) {
  return (
    <group position={[0, 0, -8.0]}>
      <mesh position={[-2.15, 1.3, 0]}>
        <boxGeometry args={[0.12, 2.6, 0.18]} />
        <meshStandardMaterial color={accent} emissive={accent} emissiveIntensity={0.55} />
      </mesh>
      <mesh position={[2.15, 1.3, 0]}>
        <boxGeometry args={[0.12, 2.6, 0.18]} />
        <meshStandardMaterial color={accent} emissive={accent} emissiveIntensity={0.55} />
      </mesh>
      <mesh position={[0, 2.58, 0]}>
        <boxGeometry args={[4.4, 0.14, 0.18]} />
        <meshStandardMaterial color={accent} emissive={accent} emissiveIntensity={0.55} />
      </mesh>
      <Html position={[0, 3.05, 0]} center distanceFactor={12} style={{ pointerEvents: "none" }}>
        <div className="scene-reception-label">AGENTSINC · SINC HEADQUARTERS</div>
      </Html>
    </group>
  );
}

function DisplayWall({ position, accent }: { position: [number, number, number]; accent: string }) {
  return (
    <group position={position}>
      <mesh position={[0, 1.65, 0]} castShadow>
        <boxGeometry args={[6.5, 3.1, 0.28]} />
        <meshStandardMaterial color="#17243A" metalness={0.42} roughness={0.48} />
      </mesh>
      <mesh position={[0, 1.7, 0.16]}>
        <planeGeometry args={[5.8, 2.45]} />
        <meshBasicMaterial color="#0B1527" />
      </mesh>
      <mesh position={[0, 1.7, 0.19]}>
        <planeGeometry args={[5.35, 2.05]} />
        <meshBasicMaterial color={accent} transparent opacity={0.055} />
      </mesh>
      <Html position={[0, 1.75, 0.22]} center distanceFactor={13} style={{ pointerEvents: "none" }}>
        <div className="scene-display-brand"><strong>AGENT<span>SINC</span></strong><small>INTELLIGENCE · NETWORK · COLLABORATION</small></div>
      </Html>
    </group>
  );
}

function Plant({ position }: { position: [number, number, number] }) {
  return (
    <group position={position}>
      <mesh position={[0, 0.25, 0]}>
        <cylinderGeometry args={[0.32, 0.25, 0.5, 8]} />
        <meshStandardMaterial color="#26354C" roughness={0.62} />
      </mesh>
      {[0, 1, 2, 3, 4].map((index) => (
        <mesh key={index} position={[Math.sin(index * 1.2) * 0.18, 0.83 + (index % 2) * 0.13, Math.cos(index * 1.2) * 0.15]} rotation={[0.2, index * 0.8, (index - 2) * 0.16]}>
          <capsuleGeometry args={[0.11, 0.65, 4, 7]} />
          <meshStandardMaterial color={index % 2 ? "#3D9B78" : "#65B78B"} roughness={0.86} />
        </mesh>
      ))}
    </group>
  );
}

function BookShelf({ position }: { position: [number, number, number] }) {
  return (
    <group position={position}>
      <mesh position={[0, 0.9, -0.15]}>
        <boxGeometry args={[1.2, 1.8, 0.3]} />
        <meshStandardMaterial color="#34415A" />
      </mesh>
      {[0.43, 0.9, 1.37].map((y) => (
        <mesh key={y} position={[0, y, 0.03]}>
          <boxGeometry args={[1.25, 0.055, 0.4]} />
          <meshStandardMaterial color="#9A805A" roughness={0.75} />
        </mesh>
      ))}
      {[0, 1, 2, 3].map((index) => (
        <mesh key={index} position={[-0.42 + index * 0.28, 0.68 + (index % 2) * 0.47, 0.03]} rotation={[0, 0, (index - 1.5) * 0.05]}>
          <boxGeometry args={[0.18, 0.42, 0.18]} />
          <meshStandardMaterial color={["#B88A56", "#5B8B95", "#9A6B72", "#D0B16C"][index]} />
        </mesh>
      ))}
    </group>
  );
}

function TestBench({ position, color }: { position: [number, number, number]; color: string }) {
  return (
    <group position={position}>
      <mesh position={[0, 0.85, -0.18]}>
        <boxGeometry args={[1.15, 0.62, 0.07]} />
        <meshStandardMaterial color="#07111F" />
      </mesh>
      <mesh position={[0, 0.85, -0.135]}>
        <planeGeometry args={[0.98, 0.48]} />
        <meshBasicMaterial color={color} />
      </mesh>
      <mesh position={[0, 0.45, 0.12]}>
        <boxGeometry args={[1.45, 0.11, 0.65]} />
        <meshStandardMaterial color="#394962" metalness={0.38} />
      </mesh>
    </group>
  );
}

function MoodWall({ position, color }: { position: [number, number, number]; color: string }) {
  return (
    <group position={position}>
      {[-0.55, 0, 0.55].map((x, index) => (
        <mesh key={x} position={[x, 1.38 + (index % 2) * 0.08, 0]} rotation={[0, -0.08, 0]}>
          <boxGeometry args={[0.45, 0.62, 0.055]} />
          <meshStandardMaterial color={index === 1 ? color : "#52637E"} emissive={index === 1 ? color : "#000000"} emissiveIntensity={0.18} />
        </mesh>
      ))}
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
  const haloRef = useRef<THREE.Mesh>(null);
  const bobOffset = useMemo(() => agent.position[0] * 0.13, [agent.position]);

  useFrame(({ clock }) => {
    if (!groupRef.current) return;
    const time = clock.elapsedTime;
    groupRef.current.position.y = Math.sin(time * 2.1 + bobOffset) * 0.025;
    if (agent.status === "collaborating") {
      groupRef.current.rotation.y = Math.sin(time * 0.45) * 0.16;
    }
    if (haloRef.current) {
      const pulse = 1 + Math.sin(time * 2.4 + bobOffset) * 0.05;
      haloRef.current.scale.setScalar(selected ? pulse : 1);
    }
  });

  const handleSelect = (event: ThreeEvent<MouseEvent>) => {
    event.stopPropagation();
    onSelect(agent.id);
  };

  return (
    <group position={[agent.position[0], 0, agent.position[2] + 1.1]} onClick={handleSelect} ref={groupRef}>
      <mesh ref={haloRef} rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.08, 0]}>
        <torusGeometry args={[selected ? 0.75 : 0.55, selected ? 0.045 : 0.025, 8, 48]} />
        <meshBasicMaterial color={agent.color} transparent opacity={selected ? 0.88 : 0.38} />
      </mesh>
      <mesh castShadow position={[0, 0.91, 0]}>
        <capsuleGeometry args={[0.25, 0.5, 6, 12]} />
        <meshStandardMaterial color={agent.color} roughness={0.46} metalness={0.12} />
      </mesh>
      <mesh castShadow position={[0, 1.53, 0]}>
        <sphereGeometry args={[0.235, 22, 22]} />
        <meshStandardMaterial color="#E9D7C7" roughness={0.82} />
      </mesh>
      <mesh castShadow position={[0, 1.67, -0.04]}>
        <sphereGeometry args={[0.24, 16, 12, 0, Math.PI * 2, 0, Math.PI * 0.56]} />
        <meshStandardMaterial color="#202638" roughness={0.9} />
      </mesh>
      {[-0.09, 0.09].map((x) => (
        <mesh key={x} position={[x, 1.54, 0.215]}>
          <sphereGeometry args={[0.025, 8, 8]} />
          <meshBasicMaterial color="#182033" />
        </mesh>
      ))}
      <mesh castShadow position={[-0.32, 0.95, 0]} rotation={[0, 0, 0.13]}>
        <capsuleGeometry args={[0.075, 0.33, 4, 8]} />
        <meshStandardMaterial color={agent.color} roughness={0.5} />
      </mesh>
      <mesh castShadow position={[0.32, 0.95, 0]} rotation={[0, 0, -0.13]}>
        <capsuleGeometry args={[0.075, 0.33, 4, 8]} />
        <meshStandardMaterial color={agent.color} roughness={0.5} />
      </mesh>
      <mesh castShadow position={[-0.13, 0.32, 0]}>
        <capsuleGeometry args={[0.075, 0.36, 4, 8]} />
        <meshStandardMaterial color="#29364D" roughness={0.7} />
      </mesh>
      <mesh castShadow position={[0.13, 0.32, 0]}>
        <capsuleGeometry args={[0.075, 0.36, 4, 8]} />
        <meshStandardMaterial color="#29364D" roughness={0.7} />
      </mesh>
      <Html position={[0, 2.18, 0]} center distanceFactor={12} style={{ pointerEvents: "none" }}>
        <div className={selected ? "scene-agent-tag selected" : "scene-agent-tag"} style={{ "--agent-color": agent.color } as React.CSSProperties}>
          <span>{agent.name}</span>
          <small>{agent.role}</small>
        </div>
      </Html>
    </group>
  );
}
