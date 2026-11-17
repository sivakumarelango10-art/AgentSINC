"use client";

import { Html, OrbitControls } from "@react-three/drei";
import { useFrame, useThree, type ThreeEvent } from "@react-three/fiber";
import { useEffect, useMemo, useRef } from "react";
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
  { id: "command", label: "COMMAND HUB", agentId: "ceo", position: [0, -4.5] as [number, number], size: [7.2, 5.4] as [number, number], color: "#8B5CF6" },
  { id: "development", label: "DEVELOPMENT STUDIO", agentId: "developer", position: [-6.3, -0.9] as [number, number], size: [5.1, 3.8] as [number, number], color: "#0EA5E9" },
  { id: "design", label: "DESIGN STUDIO", agentId: "designer", position: [6.3, -0.9] as [number, number], size: [5.1, 3.8] as [number, number], color: "#EC4899" },
  { id: "research", label: "RESEARCH LIBRARY", agentId: "researcher", position: [-6.3, 4.25] as [number, number], size: [5.1, 3.8] as [number, number], color: "#D97706" },
  { id: "quality", label: "QUALITY LAB", agentId: "tester", position: [6.3, 4.25] as [number, number], size: [5.1, 3.8] as [number, number], color: "#16A34A" },
];

const officeLocationTargets: Record<string, Record<string, [number, number, number]>> = {
  command: {
    developer: [-1.35, 0, -4.25],
    designer: [1.35, 0, -4.25],
    researcher: [-1.35, 0, -5.25],
    tester: [1.35, 0, -5.25],
  },
  discussion: {
    ceo: [-1.65, 0, 4.15],
    team_lead: [0, 0, 4.15],
    developer: [-1.05, 0, 3.5],
    designer: [1.05, 0, 3.5],
    researcher: [-1.05, 0, 4.9],
    tester: [1.05, 0, 4.9],
  },
  meeting: {
    ceo: [0, 0, 6.15],
    team_lead: [0, 0, 7.6],
    developer: [-1.85, 0, 7.6],
    designer: [1.85, 0, 7.6],
    researcher: [-1.85, 0, 8.3],
    tester: [1.85, 0, 8.3],
  },
};

const roomTargets: Record<string, [number, number, number]> = {
  all: [0, 0.55, 0],
  command: [0, 0.65, -4.5],
  development: [-6.3, 0.55, -0.9],
  design: [6.3, 0.55, -0.9],
  research: [-6.3, 0.55, 4.25],
  quality: [6.3, 0.55, 4.25],
  discussion: [0, 0.72, 4.15],
  meeting: [0, 0.8, 7.55],
};

export function AgentSincScene({
  agents,
  selectedAgentId,
  onSelectAgent,
  palette,
  focusedRoom,
}: SceneProps) {
  const roomTarget = roomTargets[focusedRoom] ?? roomTargets.all;
  const { camera } = useThree();
  const controlsRef = useRef<any>(null);
  const avatarRefs = useRef<Record<string, THREE.Group | null>>({});
  const followState = useRef({
    selectedId: null as string | null,
    previousPosition: new THREE.Vector3(),
    focusRemaining: 0,
  });

  // A click briefly eases the view onto the selected agent. While it walks,
  // the camera follows only the avatar's world-space displacement, preserving
  // the user's orbit angle and zoom after the initial focus.
  useFrame((_, delta) => {
    if (!selectedAgentId) {
      followState.current.selectedId = null;
      return;
    }
    const avatar = avatarRefs.current[selectedAgentId];
    if (!avatar) return;
    const state = followState.current;
    if (state.selectedId !== selectedAgentId) {
      state.selectedId = selectedAgentId;
      state.previousPosition.copy(avatar.position);
      state.focusRemaining = 1.35;
    }
    const target = new THREE.Vector3(
      avatar.position.x,
      avatar.position.y + 1.12,
      avatar.position.z,
    );
    if (state.focusRemaining > 0) {
      const cameraGoal = target.clone().add(new THREE.Vector3(4.6, 3.15, 6.0));
      const blend = 1 - Math.exp(-3.8 * delta);
      camera.position.lerp(cameraGoal, blend);
      if (controlsRef.current) {
        controlsRef.current.target.lerp(target, blend);
        controlsRef.current.update();
      } else {
        camera.lookAt(target);
      }
      state.focusRemaining = Math.max(0, state.focusRemaining - delta);
    } else {
      const movement = avatar.position.clone().sub(state.previousPosition);
      if (movement.lengthSq() > 0.000001) {
        camera.position.add(movement);
        if (controlsRef.current) {
          controlsRef.current.target.add(movement);
          controlsRef.current.update();
        } else {
          camera.lookAt(target);
        }
      }
    }
    state.previousPosition.copy(avatar.position);
  });

  return (
    <>
      <color attach="background" args={["#EAF0F6"]} />
      <fog attach="fog" args={["#EAF0F6", 34, 68]} />
      <ambientLight intensity={0.78} />
      <hemisphereLight args={["#FFFFFF", "#B9C3D0", 1.35]} />
      <directionalLight
        castShadow
        position={[-8, 19, 12]}
        intensity={3.2}
        shadow-mapSize-width={2048}
        shadow-mapSize-height={2048}
        shadow-camera-left={-19}
        shadow-camera-right={19}
        shadow-camera-top={19}
        shadow-camera-bottom={-19}
        shadow-bias={-0.00012}
      />
      <pointLight position={[-9, 5, -4]} color={palette.accent} intensity={0.55} distance={25} />
      <pointLight position={[9, 5, 5]} color={palette.secondary} intensity={0.48} distance={24} />
      <pointLight position={[0, 5.2, -3]} color="#FDE68A" intensity={0.42} distance={20} />

      <OfficeFloor floorColor={palette.floor} accent={palette.accent} />
      <OfficeArchitecture accent={palette.accent} secondary={palette.secondary} />
      {roomLayout.map((room) => (
        <OfficeZone
          key={room.id}
          label={room.label}
          position={room.position}
          size={room.size}
          color={room.color}
          agent={agents.find((agent) => agent.id === room.agentId)}
          teamLead={agents.find((agent) => agent.id === "team_lead")}
          focused={focusedRoom === room.id}
        />
      ))}

      <CentralCommandHub accent={palette.accent} secondary={palette.secondary} />
      <GlassMeetingRoom accent={palette.secondary} />
      <ConferenceRoom accent={palette.accent} secondary={palette.secondary} />
      <ReceptionArch accent={palette.secondary} />
      <CeilingLights accent={palette.accent} />
      <Plant position={[-10, 0, -6.8]} />
      <Plant position={[10, 0, -6.8]} />
      <Plant position={[-10, 0, 7.2]} />
      <Plant position={[10, 0, 7.2]} />
      <DisplayWall position={[0, 0, -9.2]} accent={palette.accent} />

      {agents.map((agent) => (
        <AgentAvatar
          key={agent.id}
          agent={agent}
          selected={agent.id === selectedAgentId}
          onSelect={onSelectAgent}
          registerAvatar={(node) => { avatarRefs.current[agent.id] = node; }}
        />
      ))}

      <OrbitControls
        ref={controlsRef}
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

function OfficeArchitecture({ accent, secondary }: { accent: string; secondary: string }) {
  return (
    <group>
      <mesh position={[0, 2.65, -9.82]}>
        <boxGeometry args={[25.8, 5.4, 0.24]} />
        <meshStandardMaterial color="#F8FAFC" roughness={0.86} />
      </mesh>
      {[-10.6, -5.3, 0, 5.3, 10.6].map((x) => (
        <mesh key={x} position={[x, 2.65, -9.66]}>
          <boxGeometry args={[0.09, 5.15, 0.12]} />
          <meshStandardMaterial color="#A7B4C3" metalness={0.68} roughness={0.28} />
        </mesh>
      ))}
      {[-10.6, -5.3, 0, 5.3, 10.6].map((x, index) => (
        <mesh key={index} position={[x + 2.65, 2.65, -9.72]}>
          <boxGeometry args={[5.18, 4.65, 0.035]} />
          <meshPhysicalMaterial color="#C9E4F6" transparent opacity={0.17} roughness={0.08} metalness={0.04} transmission={0.55} thickness={0.1} />
        </mesh>
      ))}
      {[0.45, 4.85].map((y) => (
        <mesh key={y} position={[0, y, -9.6]}>
          <boxGeometry args={[25.8, 0.1, 0.16]} />
          <meshStandardMaterial color="#A7B4C3" metalness={0.68} roughness={0.28} />
        </mesh>
      ))}
      {[-12.55, 12.55].map((x) => (
        <group key={x}>
          {[-6.5, -1.8, 2.9, 7.6].map((z) => (
            <mesh key={z} position={[x, 2.35, z]}>
              <boxGeometry args={[0.22, 4.7, 0.24]} />
              <meshStandardMaterial color="#F9FAFB" roughness={0.72} />
            </mesh>
          ))}
          {[-4.2, 0.55, 5.25].map((z) => (
            <mesh key={z} position={[x, 2.4, z]}>
              <boxGeometry args={[0.09, 3.55, 3.65]} />
              <meshPhysicalMaterial color="#D8E9F8" transparent opacity={0.16} roughness={0.1} transmission={0.58} thickness={0.08} />
            </mesh>
          ))}
          {[-4.2, 0.55, 5.25].map((z) => (
            <mesh key={z} position={[x + (x > 0 ? -0.02 : 0.02), 0.55, z]}>
              <boxGeometry args={[0.34, 0.14, 3.8]} />
              <meshPhysicalMaterial color="#FFFFFF" roughness={0.3} metalness={0.08} clearcoat={0.5} />
            </mesh>
          ))}
        </group>
      ))}
      <mesh position={[0, 4.95, 0]}>
        <boxGeometry args={[25.8, 0.18, 0.2]} />
        <meshStandardMaterial color="#CBD3DC" metalness={0.42} roughness={0.36} />
      </mesh>
      {[-8.5, -3, 3, 8.5].map((x) => (
        <mesh key={x} position={[x, 4.92, 0]}>
          <boxGeometry args={[0.12, 0.16, 19.5]} />
          <meshStandardMaterial color="#D5DCE4" metalness={0.35} roughness={0.42} />
        </mesh>
      ))}
      <mesh position={[-11.9, 2.45, -6.8]}>
        <boxGeometry args={[0.16, 4.6, 0.16]} />
        <meshStandardMaterial color={accent} emissive={accent} emissiveIntensity={0.08} />
      </mesh>
      <mesh position={[11.9, 2.45, -6.8]}>
        <boxGeometry args={[0.16, 4.6, 0.16]} />
        <meshStandardMaterial color={secondary} emissive={secondary} emissiveIntensity={0.08} />
      </mesh>
    </group>
  );
}

function CeilingLights({ accent }: { accent: string }) {
  return (
    <group>
      {[-8, -2.7, 2.7, 8].map((x, index) => (
        <group key={x} position={[x, 4.42, -1 + (index % 2) * 1.8]}>
          <mesh position={[0, -0.22, 0]}>
            <cylinderGeometry args={[0.018, 0.018, 0.44, 8]} />
            <meshStandardMaterial color="#9AA7B5" metalness={0.82} roughness={0.22} />
          </mesh>
          <mesh position={[0, -0.45, 0]}>
            <boxGeometry args={[2.5, 0.1, 0.72]} />
            <meshPhysicalMaterial color="#FFFFFF" roughness={0.22} metalness={0.08} clearcoat={0.7} />
          </mesh>
          <mesh position={[0, -0.51, 0]}>
            <boxGeometry args={[2.22, 0.018, 0.52]} />
            <meshBasicMaterial color={index % 2 === 0 ? "#FFF4D6" : "#E6F4FF"} />
          </mesh>
          <pointLight position={[0, -0.58, 0]} color={index % 2 === 0 ? "#FFF1D0" : accent} intensity={0.25} distance={7} />
        </group>
      ))}
    </group>
  );
}

function OfficeFloor({ floorColor, accent }: { floorColor: string; accent: string }) {
  return (
    <group>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.12, 0]} receiveShadow>
        <planeGeometry args={[26, 20]} />
        <meshPhysicalMaterial color={floorColor} roughness={0.32} metalness={0.06} clearcoat={0.24} clearcoatRoughness={0.28} />
      </mesh>
      <gridHelper args={[26, 52, "#C7D0DB", "#E0E6ED"]} position={[0, -0.105, 0]} />
      <mesh position={[0, -0.42, 0]}>
        <boxGeometry args={[26.2, 0.55, 20.2]} />
        <meshStandardMaterial color="#D9E0E8" roughness={0.78} metalness={0.04} />
      </mesh>
      <mesh position={[0, -0.12, -10]}>
        <boxGeometry args={[26.2, 0.7, 0.18]} />
        <meshStandardMaterial color="#AAB6C4" metalness={0.36} roughness={0.42} />
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
  agent,
  teamLead,
}: {
  label: string;
  position: [number, number];
  size: [number, number];
  color: string;
  focused: boolean;
  agent?: OfficeAgent;
  teamLead?: OfficeAgent;
}) {
  const [x, z] = position;
  const [width, depth] = size;
  const opacity = focused ? 0.19 : 0.105;

  return (
    <group position={[x, 0, z]}>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.014, 0]} receiveShadow>
        <planeGeometry args={[width, depth]} />
        <meshStandardMaterial color="#FFFFFF" roughness={0.9} />
      </mesh>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.021, 0]}>
        <planeGeometry args={[width - 0.22, depth - 0.22]} />
        <meshStandardMaterial color={color} transparent opacity={focused ? 0.095 : 0.045} roughness={0.86} />
      </mesh>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.026, depth / 2 - 0.16]}>
        <planeGeometry args={[width - 0.42, 0.035]} />
        <meshBasicMaterial color={color} transparent opacity={0.68} />
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
      <Html position={[0, 2.55, -depth / 2 + 0.45]} center distanceFactor={12} style={{ pointerEvents: "none" }}>
        <div className={focused ? "scene-zone-label focused" : "scene-zone-label"} style={{ "--zone-color": color } as React.CSSProperties}>
          <i />{label}
        </div>
      </Html>
      <WorkDesk color={color} agent={agent} />
      {label.includes("COMMAND") ? (
        <WorkDesk color="#0F9D91" position={[2.05, 0, -0.65]} agent={teamLead} />
      ) : null}
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
        <meshPhysicalMaterial color="#F8FCFF" transparent opacity={0.24} roughness={0.08} metalness={0.08} transmission={0.72} thickness={0.08} />
      </mesh>
      <mesh position={[-width / 2 + 0.08, 0.95, 0]}>
        <boxGeometry args={[0.055, 1.65, depth - 0.2]} />
        <meshPhysicalMaterial color="#F8FCFF" transparent opacity={0.2} roughness={0.08} metalness={0.08} transmission={0.7} thickness={0.08} />
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

function WorkDesk({
  color,
  position = [0, 0, 0.2],
  agent,
}: {
  color: string;
  position?: [number, number, number];
  agent?: OfficeAgent;
}) {
  return (
    <group position={position}>
      <mesh castShadow receiveShadow position={[0, 0.78, -0.35]}>
        <boxGeometry args={[1.9, 0.16, 0.9]} />
        <meshPhysicalMaterial color="#B98555" roughness={0.42} metalness={0.02} clearcoat={0.2} clearcoatRoughness={0.34} />
      </mesh>
      <mesh position={[0, 0.69, -0.35]}>
        <boxGeometry args={[1.55, 0.035, 0.72]} />
        <meshStandardMaterial color="#E7D0B7" roughness={0.68} />
      </mesh>
      {[-0.78, 0.78].map((x) => [-0.7, -0.02].map((z) => (
        <mesh key={`${x}-${z}`} castShadow position={[x, 0.39, z - 0.35]}>
          <boxGeometry args={[0.095, 0.74, 0.095]} />
          <meshStandardMaterial color="#AEB8C4" metalness={0.72} roughness={0.27} />
        </mesh>
      )))}
      <mesh position={[0, 1.32, -0.65]} castShadow>
        <boxGeometry args={[1.12, 0.82, 0.09]} />
        <meshPhysicalMaterial color="#202C3D" metalness={0.62} roughness={0.17} clearcoat={0.85} />
      </mesh>
      <WorkstationScreen agent={agent} />
      <mesh position={[0, 0.87, -0.59]}>
        <boxGeometry args={[0.1, 0.13, 0.11]} />
        <meshStandardMaterial color="#AAB4C0" metalness={0.68} roughness={0.28} />
      </mesh>
      <mesh castShadow position={[0.68, 0.39, -0.18]}>
        <boxGeometry args={[0.28, 0.68, 0.64]} />
        <meshPhysicalMaterial color="#E7EBF0" roughness={0.42} metalness={0.05} />
      </mesh>
      {[0.2, 0.42, 0.64].map((y) => (
        <mesh key={y} position={[0.68, y, 0.15]}>
          <boxGeometry args={[0.16, 0.018, 0.018]} />
          <meshStandardMaterial color="#9AA6B4" metalness={0.7} roughness={0.28} />
        </mesh>
      ))}
      <mesh position={[0, 0.87, -0.02]}>
        <boxGeometry args={[0.78, 0.035, 0.22]} />
        <meshStandardMaterial color="#34445A" roughness={0.56} />
      </mesh>
      <mesh position={[0.52, 0.87, -0.02]}>
        <boxGeometry args={[0.18, 0.035, 0.2]} />
        <meshPhysicalMaterial color="#E8EDF3" roughness={0.38} />
      </mesh>
      <OfficeChair color={color} position={[0, 0, 1.05]} rotation={[0, Math.PI, 0]} />
      <DeskLamp color={color} position={[-0.72, 0.88, -0.28]} />
    </group>
  );
}

function OfficeChair({
  color,
  position,
  rotation = [0, 0, 0],
}: {
  color: string;
  position: [number, number, number];
  rotation?: [number, number, number];
}) {
  return (
    <group position={position} rotation={rotation}>
      <mesh position={[0, 0.57, 0]}>
        <boxGeometry args={[0.68, 0.13, 0.64]} />
        <meshPhysicalMaterial color={color} roughness={0.83} metalness={0.01} clearcoat={0.08} />
      </mesh>
      <mesh position={[0, 1.03, -0.25]}>
        <boxGeometry args={[0.68, 0.88, 0.13]} />
        <meshPhysicalMaterial color={color} roughness={0.85} metalness={0.01} />
      </mesh>
      <mesh position={[0, 0.29, 0]}>
        <cylinderGeometry args={[0.055, 0.055, 0.52, 10]} />
        <meshStandardMaterial color="#AEB7C2" metalness={0.82} roughness={0.24} />
      </mesh>
      <mesh position={[0, 0.025, 0]}>
        <cylinderGeometry args={[0.34, 0.34, 0.07, 16]} />
        <meshStandardMaterial color="#D6DCE3" metalness={0.62} roughness={0.32} />
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
        <meshPhysicalMaterial color="#F8FAFC" metalness={0.08} roughness={0.26} clearcoat={0.55} clearcoatRoughness={0.2} />
      </mesh>
      <mesh position={[0, 0.37, 0]}>
        <cylinderGeometry args={[1.8, 1.8, 0.045, 8]} />
        <meshStandardMaterial color={accent} emissive={accent} emissiveIntensity={0.45} />
      </mesh>
      <mesh position={[0, 0.57, 0]}>
        <cylinderGeometry args={[1.15, 1.15, 0.17, 8]} />
        <meshPhysicalMaterial color="#C7D0DA" metalness={0.22} roughness={0.32} clearcoat={0.35} />
      </mesh>
      <mesh position={[0, 0.72, 0]}>
        <cylinderGeometry args={[0.83, 0.83, 0.045, 8]} />
        <meshStandardMaterial color={secondary} emissive={secondary} emissiveIntensity={0.58} />
      </mesh>
      <mesh position={[0, 0.86, 0]}>
        <octahedronGeometry args={[0.34, 0]} />
        <meshPhysicalMaterial color="#FFFFFF" emissive={accent} emissiveIntensity={0.24} metalness={0.18} roughness={0.14} clearcoat={1} />
      </mesh>
      <Html position={[0, 1.45, 0]} center distanceFactor={12} style={{ pointerEvents: "none" }}>
        <div className="scene-center-label">SINC · COMMAND CORE</div>
      </Html>
    </group>
  );
}

function GlassMeetingRoom({ accent }: { accent: string }) {
  const seats = [
    { position: [0, 0, -1.15] as [number, number, number], rotation: 0 },
    { position: [0, 0, 1.15] as [number, number, number], rotation: Math.PI },
    { position: [-1.6, 0, 0] as [number, number, number], rotation: Math.PI / 2 },
    { position: [1.6, 0, 0] as [number, number, number], rotation: -Math.PI / 2 },
  ];
  return (
    <group position={[0, 0, 4.15]}>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.025, 0]} receiveShadow>
        <planeGeometry args={[4.7, 2.9]} />
        <meshPhysicalMaterial color="#DCE7F2" roughness={0.48} metalness={0.05} />
      </mesh>
      {[-2.3, 2.3].map((x) => (
        <mesh key={x} position={[x, 1.08, 0]}>
          <boxGeometry args={[0.065, 2.05, 2.85]} />
          <meshPhysicalMaterial color="#B9D9F6" transparent opacity={0.2} roughness={0.08} transmission={0.42} />
        </mesh>
      ))}
      <mesh position={[0, 1.08, -1.42]}>
        <boxGeometry args={[4.65, 2.05, 0.065]} />
        <meshPhysicalMaterial color="#B9D9F6" transparent opacity={0.2} roughness={0.08} transmission={0.42} />
      </mesh>
      <mesh position={[0, 0.08, -1.42]}>
        <boxGeometry args={[4.6, 0.08, 0.08]} />
        <meshStandardMaterial color={accent} emissive={accent} emissiveIntensity={0.32} />
      </mesh>
      <mesh position={[0, 0.78, 0]}>
        <cylinderGeometry args={[1.02, 1.1, 0.16, 12]} />
        <meshPhysicalMaterial color="#B9C5D4" roughness={0.3} metalness={0.18} clearcoat={0.45} />
      </mesh>
      {seats.map((seat, index) => (
        <group key={index} position={seat.position} rotation={[0, seat.rotation, 0]}>
          <OfficeChair color={accent} position={[0, 0, 0]} />
        </group>
      ))}
      <Html position={[0, 2.35, -1.48]} center distanceFactor={12} style={{ pointerEvents: "none" }}>
        <div className="scene-room-sign">DISCUSSION ROOM · 04 SEATS</div>
      </Html>
    </group>
  );
}

function ConferenceRoom({ accent, secondary }: { accent: string; secondary: string }) {
  const sideSeats = [-1.8, 0, 1.8];
  return (
    <group position={[0, 0, 7.6]}>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.025, 0]} receiveShadow>
        <planeGeometry args={[6.5, 4.55]} />
        <meshPhysicalMaterial color="#E8EEF5" roughness={0.4} metalness={0.06} />
      </mesh>
      <mesh position={[-3.2, 1.62, 0]}>
        <boxGeometry args={[0.07, 3.15, 4.45]} />
        <meshPhysicalMaterial color="#B9D9F6" transparent opacity={0.19} roughness={0.08} transmission={0.48} />
      </mesh>
      <mesh position={[3.2, 1.62, 0]}>
        <boxGeometry args={[0.07, 3.15, 4.45]} />
        <meshPhysicalMaterial color="#B9D9F6" transparent opacity={0.19} roughness={0.08} transmission={0.48} />
      </mesh>
      <mesh position={[0, 1.62, -2.22]}>
        <boxGeometry args={[6.45, 3.15, 0.07]} />
        <meshPhysicalMaterial color="#B9D9F6" transparent opacity={0.19} roughness={0.08} transmission={0.48} />
      </mesh>
      {[-2.1, 2.1].map((x) => (
        <mesh key={x} position={[x, 1.62, 2.22]}>
          <boxGeometry args={[2.25, 3.15, 0.07]} />
          <meshPhysicalMaterial color="#B9D9F6" transparent opacity={0.19} roughness={0.08} transmission={0.48} />
        </mesh>
      ))}
      {[[-3.2, -2.2], [3.2, -2.2], [-3.2, 2.2], [3.2, 2.2]].map(([x, z], index) => (
        <mesh key={index} position={[x, 1.62, z]}>
          <boxGeometry args={[0.12, 3.2, 0.12]} />
          <meshStandardMaterial color="#93A5BB" metalness={0.62} roughness={0.26} />
        </mesh>
      ))}
      <mesh position={[0, 0.81, 0]}>
        <boxGeometry args={[5.0, 0.16, 1.35]} />
        <meshPhysicalMaterial color="#9E795C" roughness={0.36} metalness={0.03} clearcoat={0.24} />
      </mesh>
      <mesh position={[0, 0.91, 0]}>
        <boxGeometry args={[4.55, 0.035, 1.08]} />
        <meshStandardMaterial color="#D8C4AE" roughness={0.55} />
      </mesh>
      {sideSeats.map((x) => (
        <group key={"north-" + x} position={[x, 0, -1.35]}>
          <OfficeChair color={secondary} position={[0, 0, 0]} />
        </group>
      ))}
      {sideSeats.map((x) => (
        <group key={"south-" + x} position={[x, 0, 1.35]} rotation={[0, Math.PI, 0]}>
          <OfficeChair color={secondary} position={[0, 0, 0]} />
        </group>
      ))}
      {[{ x: -2.68, rotation: Math.PI / 2 }, { x: 2.68, rotation: -Math.PI / 2 }].map((seat) => (
        <group key={seat.x} position={[seat.x, 0, 0]} rotation={[0, seat.rotation, 0]}>
          <OfficeChair color={secondary} position={[0, 0, 0]} />
        </group>
      ))}
      <mesh position={[0, 1.95, -2.13]}>
        <boxGeometry args={[2.4, 1.1, 0.08]} />
        <meshPhysicalMaterial color="#25364D" metalness={0.32} roughness={0.2} clearcoat={0.65} />
      </mesh>
      <mesh position={[0, 1.95, -2.075]}>
        <planeGeometry args={[2.16, 0.86]} />
        <meshBasicMaterial color={accent} />
      </mesh>
      <Html position={[0, 2.8, -2.24]} center distanceFactor={12} style={{ pointerEvents: "none" }}>
        <div className="scene-room-sign">SINC MEETING ROOM · 08 SEATS</div>
      </Html>
    </group>
  );
}

function ReceptionArch({ accent }: { accent: string }) {
  return (
    <group position={[0, 0, -8.0]}>
      <mesh position={[-2.15, 1.3, 0]}>
        <boxGeometry args={[0.12, 2.6, 0.18]} />
        <meshStandardMaterial color={accent} emissive={accent} emissiveIntensity={0.22} />
      </mesh>
      <mesh position={[2.15, 1.3, 0]}>
        <boxGeometry args={[0.12, 2.6, 0.18]} />
        <meshPhysicalMaterial color="#F8FAFC" metalness={0.28} roughness={0.24} clearcoat={0.7} />
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
        <meshPhysicalMaterial color="#F7F8FA" metalness={0.12} roughness={0.28} clearcoat={0.4} />
      </mesh>
      <mesh position={[0, 1.7, 0.16]}>
        <planeGeometry args={[5.8, 2.45]} />
        <meshBasicMaterial color="#EAF2FA" />
      </mesh>
      <mesh position={[0, 1.7, 0.19]}>
        <planeGeometry args={[5.35, 2.05]} />
        <meshBasicMaterial color={accent} transparent opacity={0.12} />
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
        <meshPhysicalMaterial color="#F8FAFC" roughness={0.34} metalness={0.02} clearcoat={0.55} />
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
        <meshPhysicalMaterial color="#E7E2D9" roughness={0.58} />
      </mesh>
      {[0.43, 0.9, 1.37].map((y) => (
        <mesh key={y} position={[0, y, 0.03]}>
          <boxGeometry args={[1.25, 0.055, 0.4]} />
          <meshStandardMaterial color="#B98555" roughness={0.62} />
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
        <meshPhysicalMaterial color="#DCE2E9" metalness={0.22} roughness={0.3} />
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
  registerAvatar,
}: {
  agent: OfficeAgent;
  selected: boolean;
  onSelect: (id: string) => void;
  registerAvatar: (node: THREE.Group | null) => void;
}) {
  const groupRef = useRef<THREE.Group>(null);
  const torsoRef = useRef<THREE.Group>(null);
  const headRef = useRef<THREE.Group>(null);
  const leftArmRef = useRef<THREE.Group>(null);
  const rightArmRef = useRef<THREE.Group>(null);
  const haloRef = useRef<THREE.Mesh>(null);
  const leftLegRef = useRef<THREE.Group>(null);
  const rightLegRef = useRef<THREE.Group>(null);
  const sitPoseRef = useRef(0);
  const homePosition: [number, number, number] = [
    agent.position[0], 0, agent.position[2] + 1.1,
  ];
  const destination = agent.location && agent.location !== "desk" && agent.location !== "command"
    ? officeLocationTargets[agent.location]?.[agent.id] ?? homePosition
    : agent.location === "command"
      ? officeLocationTargets.command?.[agent.id] ?? homePosition
      : homePosition;
  const bobOffset = useMemo(() => agent.position[0] * 0.13, [agent.position]);
  const skinTone = agent.id === "researcher" ? "#B97852" : agent.id === "designer" ? "#D69B76" : agent.id === "tester" ? "#C58C69" : "#D29A75";
  const hairTone = agent.id === "designer" ? "#302322" : agent.id === "researcher" ? "#241D19" : "#302A28";
  const wearsGlasses = agent.id === "tester" || agent.id === "researcher";
  const isPaused = agent.status === "paused";

  useFrame(({ clock }, delta) => {
    const time = clock.elapsedTime;
    const breathing = Math.sin(time * 1.65 + bobOffset) * 0.012;
    let walking = false;
    if (groupRef.current) {
      const currentX = groupRef.current.position.x;
      const currentZ = groupRef.current.position.z;
      const remaining = Math.hypot(destination[0] - currentX, destination[2] - currentZ);
      walking = remaining > 0.075;
      groupRef.current.position.x = THREE.MathUtils.damp(currentX, destination[0], 1.55, delta);
      groupRef.current.position.z = THREE.MathUtils.damp(currentZ, destination[2], 1.55, delta);
      groupRef.current.position.y = walking
        ? Math.abs(Math.sin(time * 10 + bobOffset)) * 0.045
        : Math.sin(time * 1.8 + bobOffset) * 0.012;
      const socialCenter = agent.location === "discussion"
        ? [0, 0, 4.15] as [number, number, number]
        : agent.location === "meeting"
          ? [0, 0, 7.6] as [number, number, number]
          : null;
      const heading = walking
        ? Math.atan2(destination[0] - currentX, destination[2] - currentZ)
        : socialCenter
          ? Math.atan2(socialCenter[0] - currentX, socialCenter[2] - currentZ)
          : Math.PI;
      groupRef.current.rotation.y = THREE.MathUtils.damp(
        groupRef.current.rotation.y, heading, 7, delta
      );
    }
    const destinationIsSeat = agent.location === "desk" ||
      agent.location === "discussion" || agent.location === "meeting";
    const wantsToSit = !walking && destinationIsSeat &&
      agent.status !== "paused" && agent.status !== "failed";
    sitPoseRef.current = THREE.MathUtils.damp(
      sitPoseRef.current, wantsToSit ? 1 : 0, 5.5, delta
    );
    const sitPose = sitPoseRef.current;
    if (torsoRef.current) {
      torsoRef.current.position.y = 1.02 - sitPose * 0.13 + breathing;
      torsoRef.current.rotation.x = walking ? -0.075 : sitPose * 0.035;
    }
    const stride = walking ? Math.sin(time * 10 + bobOffset) * 0.42 : 0;
    if (leftLegRef.current) leftLegRef.current.rotation.x = stride - sitPose * 0.22;
    if (rightLegRef.current) rightLegRef.current.rotation.x = -stride - sitPose * 0.22;
    if (headRef.current) {
      const thinkingTilt = agent.status === "thinking" ? 0.09 : 0;
      headRef.current.rotation.z = thinkingTilt + Math.sin(time * 0.7 + bobOffset) * 0.012;
      headRef.current.rotation.y = agent.status === "collaborating" ? Math.sin(time * 0.55) * 0.14 : 0;
    }
    const workMotion = agent.status === "working" ? Math.sin(time * 3.2 + bobOffset) * 0.045 : 0;
    const talkMotion = agent.status === "collaborating" ? Math.sin(time * 2.2 + bobOffset) * 0.08 : 0;
    const walkArmSwing = walking ? Math.sin(time * 10 + bobOffset) * 0.24 : 0;
    if (leftArmRef.current) {
      leftArmRef.current.rotation.x = -0.12 + workMotion - talkMotion + walkArmSwing;
      leftArmRef.current.rotation.z = 0.12 + (isPaused ? 0 : talkMotion * 0.35);
    }
    if (rightArmRef.current) {
      rightArmRef.current.rotation.x = -0.12 - workMotion + talkMotion - walkArmSwing;
      rightArmRef.current.rotation.z = -0.12 - (isPaused ? 0 : talkMotion * 0.35);
    }
    if (haloRef.current) {
      const pulse = 1 + Math.sin(time * 2.1 + bobOffset) * 0.035;
      haloRef.current.scale.setScalar(selected ? pulse : 1);
    }
  });

  const handleSelect = (event: ThreeEvent<MouseEvent>) => {
    event.stopPropagation();
    onSelect(agent.id);
  };

  return (
    <group
      position={homePosition}
      rotation={[0, Math.PI, 0]}
      onClick={handleSelect}
      ref={(node) => {
        groupRef.current = node;
        registerAvatar(node);
      }}
    >
      <mesh ref={haloRef} rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.075, 0]}>
        <torusGeometry args={[selected ? 0.72 : 0.56, selected ? 0.038 : 0.022, 10, 56]} />
        <meshBasicMaterial color={agent.color} transparent opacity={selected ? 0.78 : 0.28} />
      </mesh>

      <group ref={torsoRef} position={[0, 1.02, 0]}>
        <mesh castShadow receiveShadow>
          <capsuleGeometry args={[0.285, 0.43, 8, 18]} />
          <meshPhysicalMaterial color={agent.color} roughness={0.78} metalness={0.015} clearcoat={0.08} />
        </mesh>
        <mesh position={[0, 0.05, 0.246]}>
          <boxGeometry args={[0.16, 0.43, 0.018]} />
          <meshPhysicalMaterial color="#F8FAFC" roughness={0.72} />
        </mesh>
        <mesh position={[0, 0.27, 0.235]} rotation={[0.12, 0, 0]}>
          <coneGeometry args={[0.105, 0.19, 4]} />
          <meshStandardMaterial color="#F7F8FA" roughness={0.8} />
        </mesh>
        <mesh position={[0, -0.28, 0]}>
          <boxGeometry args={[0.42, 0.055, 0.28]} />
          <meshStandardMaterial color="#27364C" roughness={0.68} />
        </mesh>
        {agent.id === "ceo" ? (
          <mesh position={[0, 0.02, 0.268]}>
            <coneGeometry args={[0.035, 0.22, 4]} />
            <meshStandardMaterial color="#7C3AED" roughness={0.62} />
          </mesh>
        ) : null}
      </group>

      <group ref={headRef} position={[0, 1.73, 0]}>
        <mesh castShadow>
          <sphereGeometry args={[0.235, 32, 28]} />
          <meshPhysicalMaterial color={skinTone} roughness={0.86} metalness={0} sheen={0.16} sheenRoughness={0.75} />
        </mesh>
        <mesh position={[0, -0.28, 0]}>
          <cylinderGeometry args={[0.085, 0.095, 0.2, 16]} />
          <meshStandardMaterial color={skinTone} roughness={0.86} />
        </mesh>
        <mesh position={[0, 0.115, -0.028]} scale={[1.04, 0.57, 1.03]}>
          <sphereGeometry args={[0.242, 26, 18, 0, Math.PI * 2, 0, 1.28]} />
          <meshStandardMaterial color={hairTone} roughness={0.92} />
        </mesh>
        <mesh position={[0, -0.015, -0.18]} scale={[0.9, 0.9, 0.48]}>
          <sphereGeometry args={[0.22, 18, 16]} />
          <meshStandardMaterial color={hairTone} roughness={0.95} />
        </mesh>
        {[-1, 1].map((side) => (
          <group key={side}>
            <mesh position={[side * 0.235, -0.015, 0]}>
              <sphereGeometry args={[0.055, 14, 14]} />
              <meshPhysicalMaterial color={skinTone} roughness={0.86} />
            </mesh>
            <mesh position={[side * 0.082, 0.025, 0.206]}>
              <sphereGeometry args={[0.045, 16, 14]} />
              <meshBasicMaterial color="#FBFCFE" />
            </mesh>
            <mesh position={[side * 0.082, 0.025, 0.244]}>
              <sphereGeometry args={[0.021, 12, 12]} />
              <meshBasicMaterial color="#293243" />
            </mesh>
            <mesh position={[side * 0.082, 0.083, 0.205]} rotation={[0, 0, side * -0.08]}>
              <boxGeometry args={[0.082, 0.018, 0.018]} />
              <meshStandardMaterial color={hairTone} roughness={0.9} />
            </mesh>
          </group>
        ))}
        <mesh position={[0, -0.045, 0.241]} rotation={[Math.PI / 2, 0, 0]}>
          <coneGeometry args={[0.038, 0.088, 9]} />
          <meshPhysicalMaterial color={skinTone} roughness={0.82} />
        </mesh>
        <mesh position={[0, -0.135, 0.212]}>
          <boxGeometry args={[0.07, 0.012, 0.012]} />
          <meshStandardMaterial color="#8B514A" roughness={0.88} />
        </mesh>
        {wearsGlasses ? (
          <group>
            {[-0.082, 0.082].map((side) => (
              <mesh key={side} position={[side, 0.025, 0.25]}>
                <torusGeometry args={[0.049, 0.008, 6, 24]} />
                <meshStandardMaterial color="#475569" metalness={0.8} roughness={0.25} />
              </mesh>
            ))}
            <mesh position={[0, 0.025, 0.25]}>
              <boxGeometry args={[0.035, 0.012, 0.012]} />
              <meshStandardMaterial color="#475569" metalness={0.8} roughness={0.25} />
            </mesh>
          </group>
        ) : null}
      </group>

      {[-0.13, 0.13].map((side, index) => (
        <group
          key={side}
          ref={index === 0 ? leftLegRef : rightLegRef}
          position={[side, 0.72, 0.05]}
        >
          <mesh castShadow position={[0, -0.02, 0.24]} rotation={[Math.PI / 2, 0, 0]}>
            <capsuleGeometry args={[0.09, 0.34, 6, 12]} />
            <meshPhysicalMaterial color="#45536A" roughness={0.86} />
          </mesh>
          <mesh castShadow position={[0, -0.32, 0.48]}>
            <capsuleGeometry args={[0.078, 0.29, 6, 12]} />
            <meshPhysicalMaterial color="#45536A" roughness={0.86} />
          </mesh>
          <mesh castShadow position={[0, -0.55, 0.58]} scale={[1, 0.62, 1.52]}>
            <sphereGeometry args={[0.115, 18, 14]} />
            <meshPhysicalMaterial color="#253247" roughness={0.55} />
          </mesh>
        </group>
      ))}

      <group ref={leftArmRef} position={[-0.32, 1.27, 0]}>
        <mesh castShadow position={[0, -0.17, 0]}>
          <capsuleGeometry args={[0.115, 0.32, 6, 12]} />
          <meshPhysicalMaterial color={agent.color} roughness={0.82} />
        </mesh>
        <mesh castShadow position={[0, -0.48, 0.015]}>
          <capsuleGeometry args={[0.078, 0.28, 6, 12]} />
          <meshPhysicalMaterial color={skinTone} roughness={0.86} />
        </mesh>
        <mesh castShadow position={[0, -0.66, 0.035]}>
          <sphereGeometry args={[0.082, 16, 14]} />
          <meshPhysicalMaterial color={skinTone} roughness={0.86} />
        </mesh>
      </group>
      <group ref={rightArmRef} position={[0.32, 1.27, 0]}>
        <mesh castShadow position={[0, -0.17, 0]}>
          <capsuleGeometry args={[0.115, 0.32, 6, 12]} />
          <meshPhysicalMaterial color={agent.color} roughness={0.82} />
        </mesh>
        <mesh castShadow position={[0, -0.48, 0.015]}>
          <capsuleGeometry args={[0.078, 0.28, 6, 12]} />
          <meshPhysicalMaterial color={skinTone} roughness={0.86} />
        </mesh>
        <mesh castShadow position={[0, -0.66, 0.035]}>
          <sphereGeometry args={[0.082, 16, 14]} />
          <meshPhysicalMaterial color={skinTone} roughness={0.86} />
        </mesh>
      </group>

    </group>
  );
}


/** Paint the live task view onto the actual monitor plane. There is no DOM
 * overlay or second floating panel in the 3D scene. */
function WorkstationScreen({ agent }: { agent?: OfficeAgent }) {
  const display = useMemo(() => {
    if (typeof document === "undefined") return null;
    const canvas = document.createElement("canvas");
    canvas.width = 1024;
    canvas.height = 700;
    const texture = new THREE.CanvasTexture(canvas);
    texture.colorSpace = THREE.SRGBColorSpace;
    texture.minFilter = THREE.LinearMipmapLinearFilter;
    texture.magFilter = THREE.LinearFilter;
    return { canvas, texture };
  }, []);

  useEffect(() => {
    if (!display) return;
    const context = display.canvas.getContext("2d");
    if (!context) return;

    const { canvas } = display;
    const width = canvas.width;
    const height = canvas.height;
    const status = agent?.taskStatus ?? "idle";
    const accent = agent?.color ?? "#2676E8";
    const title = agent?.currentTask && agent.currentTask !== "No active mission assigned"
      ? agent.currentTask
      : "No active mission";
    const activity = agent?.latestActivity || "Waiting for a task assignment.";
    const result = agent?.latestResult || "";

    context.clearRect(0, 0, width, height);
    context.fillStyle = "#0B1220";
    context.fillRect(0, 0, width, height);

    // Desktop title bar and application chrome.
    context.fillStyle = "#172235";
    context.fillRect(0, 0, width, 68);
    context.fillStyle = "#EAF2FC";
    context.font = "700 23px Inter, Arial, sans-serif";
    context.fillText(agent?.department?.toUpperCase() ?? "SINC WORKSTATION", 34, 42);
    context.fillStyle = accent;
    context.beginPath();
    context.arc(966, 34, 9, 0, Math.PI * 2);
    context.fill();
    context.fillStyle = "#9FB0C7";
    context.font = "600 18px Inter, Arial, sans-serif";
    context.fillText(agent?.name ?? "Agent", 34, 104);

    // A status indicator tied to the actual task lifecycle.
    const stateColor = status === "running" ? "#4ADE80"
      : status === "queued" ? "#FBBF24"
        : status === "failed" ? "#F87171"
          : status === "completed" ? "#60A5FA"
            : "#94A3B8";
    context.fillStyle = "#1A2A3E";
    context.fillRect(34, 132, 956, 54);
    context.fillStyle = stateColor;
    context.beginPath();
    context.arc(58, 159, 8, 0, Math.PI * 2);
    context.fill();
    context.fillStyle = "#E8F0FB";
    context.font = "700 19px Inter, Arial, sans-serif";
    context.fillText(status.toUpperCase(), 82, 166);
    context.fillStyle = "#A9B8CC";
    context.font = "600 17px Inter, Arial, sans-serif";
    context.textAlign = "right";
    context.fillText(agent ? `${agent.progress}%` : "—", 966, 166);
    context.textAlign = "left";

    context.fillStyle = "#8EA2BC";
    context.font = "700 17px Inter, Arial, sans-serif";
    context.fillText("CURRENT ASSIGNMENT", 34, 230);
    context.fillStyle = "#F1F6FD";
    context.font = "700 25px Inter, Arial, sans-serif";
    drawCanvasLines(context, title, 34, 270, 920, 34, 2);

    context.fillStyle = "#8EA2BC";
    context.font = "700 17px Inter, Arial, sans-serif";
    context.fillText("LATEST RECORDED ACTIVITY", 34, 370);
    context.fillStyle = "#D6E1EF";
    context.font = "500 19px Inter, Arial, sans-serif";
    drawCanvasLines(context, activity, 34, 408, 920, 29, 3);

    if (result) {
      context.fillStyle = "#8EA2BC";
      context.font = "700 15px Inter, Arial, sans-serif";
      context.fillText(status === "completed" ? "LATEST RESULT" : "LATEST OUTPUT", 34, 542);
      context.fillStyle = "#9EB0C7";
      context.font = "500 16px Inter, Arial, sans-serif";
      drawCanvasLines(context, result.replace(/\s+/g, " "), 34, 574, 920, 23, 3);
    }

    // Progress is rendered only from the backend's persisted task progress.
    context.fillStyle = "#26364B";
    context.fillRect(34, 652, 920, 10);
    context.fillStyle = accent;
    context.fillRect(34, 652, Math.max(0, Math.min(100, agent?.progress ?? 0)) * 9.2, 10);
    context.fillStyle = "#8296B0";
    context.font = "500 13px Inter, Arial, sans-serif";
    context.fillText("AGENTSINC LOCAL RUNTIME · LIVE TASK DATA", 34, 686);
    if (agent?.latestTaskUpdatedAt) {
      context.textAlign = "right";
      context.fillText(new Date(agent.latestTaskUpdatedAt).toLocaleString(), 966, 686);
      context.textAlign = "left";
    }
    display.texture.needsUpdate = true;
  }, [
    display,
    agent?.name,
    agent?.department,
    agent?.color,
    agent?.status,
    agent?.taskStatus,
    agent?.currentTask,
    agent?.latestActivity,
    agent?.latestResult,
    agent?.progress,
    agent?.latestTaskUpdatedAt,
  ]);

  useEffect(() => () => display?.texture.dispose(), [display]);

  if (!display) {
    return (
      <mesh position={[0, 1.32, -0.6]}>
        <planeGeometry args={[0.98, 0.68]} />
        <meshBasicMaterial color="#0B1220" />
      </mesh>
    );
  }
  return (
    <mesh position={[0, 1.32, -0.598]}>
      <planeGeometry args={[0.98, 0.68]} />
      <meshBasicMaterial map={display.texture} toneMapped={false} />
    </mesh>
  );
}

function drawCanvasLines(
  context: CanvasRenderingContext2D,
  value: string,
  x: number,
  y: number,
  maxWidth: number,
  lineHeight: number,
  maxLines: number,
) {
  const words = String(value || "").split(/\s+/);
  let line = "";
  let lineNumber = 0;
  for (const word of words) {
    const candidate = line ? `${line} ${word}` : word;
    if (context.measureText(candidate).width > maxWidth && line) {
      context.fillText(line, x, y + lineNumber * lineHeight);
      line = word;
      lineNumber += 1;
      if (lineNumber >= maxLines) return;
    } else {
      line = candidate;
    }
  }
  if (line && lineNumber < maxLines) {
    context.fillText(line, x, y + lineNumber * lineHeight);
  }
}
