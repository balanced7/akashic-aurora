"use client";

import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { useEffect, useMemo, useRef, useState } from "react";
import * as THREE from "three";

import { AGENTS } from "~/modules/marketing/home/constellation-data";

import type { ConstellationEvent } from "~/modules/marketing/home/constellation-data";

/**
 * "One record, every agent" in 3D. A gold wireframe core is the append-only record.
 * Agent seats orbit it. Gold pulses travel in (learn), cyan pulses travel out (recall at action).
 * A field of points around the core stands for stored lessons.
 */

const GOLD = new THREE.Color("#c8aa6e");
const GOLD_BRIGHT = new THREE.Color("#f0e6d2");
const CYAN = new THREE.Color("#0ac8b9");
const CYAN_BRIGHT = new THREE.Color("#b8fff8");

const ORBIT_RADIUS = 3.05;
const PULSE_COUNT = 10;

interface Pulse {
  agent: number;
  kind: ConstellationEvent["kind"];
  progress: number;
  speed: number;
}

interface SceneProps {
  readonly labelRefs: React.RefObject<(HTMLSpanElement | null)[]>;
  readonly onEvent: (event: ConstellationEvent) => void;
  readonly reduced: boolean;
}

const agentPosition = (index: number, time: number, target: THREE.Vector3) => {
  const angle = (index / AGENTS.length) * Math.PI * 2 + time * 0.06;
  const tilt = Math.sin(angle * 2 + index) * 0.55;
  return target.set(
    Math.cos(angle) * ORBIT_RADIUS,
    tilt,
    Math.sin(angle) * ORBIT_RADIUS,
  );
};

const Core = () => {
  const ref = useRef<THREE.Group>(null);
  const edges = useMemo(
    () => new THREE.EdgesGeometry(new THREE.IcosahedronGeometry(1.05, 1)),
    [],
  );
  const inner = useMemo(
    () => new THREE.EdgesGeometry(new THREE.IcosahedronGeometry(0.62, 0)),
    [],
  );

  useFrame((_, delta) => {
    if (!ref.current) return;
    ref.current.rotation.y += delta * 0.18;
    ref.current.rotation.x += delta * 0.05;
  });

  return (
    <group ref={ref}>
      <lineSegments geometry={edges}>
        <lineBasicMaterial color={GOLD} transparent opacity={0.85} />
      </lineSegments>
      <lineSegments geometry={inner} rotation={[0.6, 0.3, 0]}>
        <lineBasicMaterial color={CYAN_BRIGHT} transparent opacity={0.6} />
      </lineSegments>
      <mesh>
        <sphereGeometry args={[0.42, 32, 32]} />
        <meshBasicMaterial
          color={CYAN}
          transparent
          opacity={0.35}
          blending={THREE.AdditiveBlending}
        />
      </mesh>
      <mesh>
        <sphereGeometry args={[0.9, 32, 32]} />
        <meshBasicMaterial
          color={CYAN}
          transparent
          opacity={0.06}
          blending={THREE.AdditiveBlending}
          depthWrite={false}
        />
      </mesh>
    </group>
  );
};

/** Stored lessons: a slowly turning disc of points, denser near the core. */
const LessonField = () => {
  const ref = useRef<THREE.Points>(null);
  const geometry = useMemo(() => {
    const count = 1400;
    const positions = new Float32Array(count * 3);
    const colors = new Float32Array(count * 3);
    const color = new THREE.Color();
    for (let index = 0; index < count; index++) {
      const radius = 1.4 + Math.pow(Math.random(), 1.8) * 4.8;
      const angle = Math.random() * Math.PI * 2;
      const spread = (Math.random() - 0.5) * (0.25 + radius * 0.18);
      positions[index * 3] = Math.cos(angle) * radius;
      positions[index * 3 + 1] = spread;
      positions[index * 3 + 2] = Math.sin(angle) * radius;
      color
        .copy(Math.random() < 0.18 ? GOLD : CYAN)
        .lerp(new THREE.Color("#ffffff"), Math.random() * 0.25);
      colors.set([color.r, color.g, color.b], index * 3);
    }
    const buffer = new THREE.BufferGeometry();
    buffer.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    buffer.setAttribute("color", new THREE.BufferAttribute(colors, 3));
    return buffer;
  }, []);

  useFrame((_, delta) => {
    if (ref.current) ref.current.rotation.y -= delta * 0.025;
  });

  return (
    <points ref={ref} geometry={geometry}>
      <pointsMaterial
        size={0.035}
        vertexColors
        transparent
        opacity={0.75}
        sizeAttenuation
        blending={THREE.AdditiveBlending}
        depthWrite={false}
      />
    </points>
  );
};

const OrbitRing = () => {
  const geometry = useMemo(() => {
    const points = Array.from({ length: 129 }, (_, index) => {
      const angle = (index / 128) * Math.PI * 2;
      return new THREE.Vector3(
        Math.cos(angle) * ORBIT_RADIUS,
        0,
        Math.sin(angle) * ORBIT_RADIUS,
      );
    });
    return new THREE.BufferGeometry().setFromPoints(points);
  }, []);
  return (
    <lineLoop geometry={geometry}>
      <lineDashedMaterial color="#ffffff" transparent opacity={0.08} />
    </lineLoop>
  );
};

/** Agent seats, their links to the core, and the pulses that travel along them. */
const Agents = ({ labelRefs, onEvent, reduced }: SceneProps) => {
  const nodes = useRef<(THREE.Mesh | null)[]>([]);
  const halos = useRef<(THREE.Mesh | null)[]>([]);
  const linkGeometry = useMemo(() => {
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute(
      "position",
      new THREE.BufferAttribute(new Float32Array(AGENTS.length * 6), 3),
    );
    return geometry;
  }, []);
  const pulses = useMemo<Pulse[]>(
    () =>
      Array.from({ length: PULSE_COUNT }, (_, index) => ({
        agent: index % AGENTS.length,
        kind: index % 2 === 0 ? "learn" : "recall",
        progress: Math.random(),
        speed: 0.28 + Math.random() * 0.22,
      })),
    [],
  );
  const pulseMeshes = useRef<(THREE.Mesh | null)[]>([]);
  const { camera, size } = useThree();
  const scratch = useMemo(
    () => ({ position: new THREE.Vector3(), projected: new THREE.Vector3() }),
    [],
  );
  const positions = useMemo(() => AGENTS.map(() => new THREE.Vector3()), []);

  useFrame((state, delta) => {
    const time = reduced ? 8 : state.clock.elapsedTime;
    const link = linkGeometry.getAttribute("position") as THREE.BufferAttribute;

    AGENTS.forEach((_, index) => {
      const position = agentPosition(
        index,
        time,
        positions[index] ?? scratch.position,
      );
      nodes.current[index]?.position.copy(position);
      const halo = halos.current[index];
      if (halo) {
        halo.position.copy(position);
        halo.lookAt(camera.position);
      }
      link.setXYZ(index * 2, 0, 0, 0);
      link.setXYZ(index * 2 + 1, position.x, position.y, position.z);

      // Project each seat to screen space so the DOM labels follow it (world space, after the rig turns).
      const label = labelRefs.current[index];
      const node = nodes.current[index];
      if (label && node) {
        node.getWorldPosition(scratch.projected).project(camera);
        const x = (scratch.projected.x * 0.5 + 0.5) * size.width;
        const y = (-scratch.projected.y * 0.5 + 0.5) * size.height;
        const depth = THREE.MathUtils.clamp(
          1.15 - scratch.projected.z * 0.6,
          0.35,
          1,
        );
        label.style.transform = `translate3d(${x}px, ${y}px, 0) translate(-50%, -170%)`;
        label.style.opacity = String(depth);
      }
    });
    link.needsUpdate = true;

    pulses.forEach((pulse, index) => {
      if (!reduced) pulse.progress += delta * pulse.speed;
      if (pulse.progress >= 1) {
        onEvent({ agent: AGENTS[pulse.agent] ?? "agent", kind: pulse.kind });
        pulse.progress = 0;
        pulse.agent = Math.floor(Math.random() * AGENTS.length);
        pulse.kind = Math.random() < 0.5 ? "learn" : "recall";
        pulse.speed = 0.28 + Math.random() * 0.22;
      }
      const mesh = pulseMeshes.current[index];
      const from = positions[pulse.agent];
      if (!mesh || !from) return;
      // Learn travels seat to core; recall travels core to seat. Ease along a slight arc.
      const t = pulse.kind === "learn" ? pulse.progress : 1 - pulse.progress;
      const eased = t * t * (3 - 2 * t);
      mesh.position.copy(from).multiplyScalar(1 - eased);
      mesh.position.y += Math.sin(eased * Math.PI) * 0.35;
      const material = mesh.material as THREE.MeshBasicMaterial;
      material.color
        .copy(pulse.kind === "learn" ? GOLD : CYAN)
        .multiplyScalar(1.6);
      mesh.scale.setScalar(0.6 + Math.sin(pulse.progress * Math.PI) * 0.8);
    });
  });

  return (
    <group>
      <lineSegments geometry={linkGeometry}>
        <lineBasicMaterial color="#ffffff" transparent opacity={0.07} />
      </lineSegments>
      {AGENTS.map((agent, index) => (
        <group key={agent}>
          <mesh ref={(mesh) => void (nodes.current[index] = mesh)}>
            <sphereGeometry args={[0.11, 24, 24]} />
            <meshBasicMaterial color={index % 3 === 0 ? GOLD : CYAN} />
          </mesh>
          <mesh ref={(mesh) => void (halos.current[index] = mesh)}>
            <ringGeometry args={[0.18, 0.2, 48]} />
            <meshBasicMaterial
              color={index % 3 === 0 ? GOLD : CYAN}
              transparent
              opacity={0.6}
              side={THREE.DoubleSide}
            />
          </mesh>
        </group>
      ))}
      {pulses.map((_, index) => (
        <mesh
          key={index}
          ref={(mesh) => void (pulseMeshes.current[index] = mesh)}
        >
          <sphereGeometry args={[0.07, 16, 16]} />
          <meshBasicMaterial
            color={GOLD_BRIGHT}
            transparent
            opacity={0.95}
            blending={THREE.AdditiveBlending}
          />
        </mesh>
      ))}
    </group>
  );
};

/** Pull the camera back on narrow canvases so the whole orbit stays in frame. */
const CameraFit = () => {
  const { camera, size } = useThree();
  useEffect(() => {
    const aspect = size.width / Math.max(1, size.height);
    camera.position.z = Math.max(7.2, 9.6 / aspect);
    camera.updateProjectionMatrix();
  }, [camera, size]);
  return null;
};

/** Pointer parallax plus a slow drift; drag to turn the whole constellation. */
const Rig = ({ children }: { children: React.ReactNode }) => {
  const ref = useRef<THREE.Group>(null);
  const drag = useRef({ active: false, lastX: 0, spin: 0 });
  const { gl } = useThree();

  useEffect(() => {
    const element = gl.domElement;
    const down = (event: PointerEvent) => {
      drag.current.active = true;
      drag.current.lastX = event.clientX;
    };
    const move = (event: PointerEvent) => {
      if (!drag.current.active) return;
      drag.current.spin += (event.clientX - drag.current.lastX) * 0.006;
      drag.current.lastX = event.clientX;
    };
    const up = () => void (drag.current.active = false);
    element.addEventListener("pointerdown", down);
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", up);
    return () => {
      element.removeEventListener("pointerdown", down);
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", up);
    };
  }, [gl]);

  useFrame((state, delta) => {
    if (!ref.current) return;
    const targetX = state.pointer.y * 0.18 + 0.32;
    ref.current.rotation.x += (targetX - ref.current.rotation.x) * 0.05;
    ref.current.rotation.y +=
      delta * 0.04 + (drag.current.spin - ref.current.rotation.y) * 0.08;
    drag.current.spin = ref.current.rotation.y;
  });

  return <group ref={ref}>{children}</group>;
};

export const ConstellationScene = ({
  labelRefs,
  onEvent,
}: Omit<SceneProps, "reduced">) => {
  const [reduced, setReduced] = useState(false);
  const [active, setActive] = useState(true);
  const wrapper = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setReduced(window.matchMedia("(prefers-reduced-motion: reduce)").matches);
    const element = wrapper.current;
    if (!element) return;
    const observer = new IntersectionObserver(([entry]) =>
      setActive(Boolean(entry?.isIntersecting)),
    );
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  return (
    <div ref={wrapper} className="absolute inset-0">
      <Canvas
        dpr={[1, 1.5]}
        frameloop={active && !reduced ? "always" : "demand"}
        camera={{ position: [0, 1.4, 7.2], fov: 42 }}
        gl={{
          antialias: true,
          alpha: true,
          powerPreference: "high-performance",
        }}
        data-testid="constellation-canvas"
        style={{ cursor: "grab" }}
      >
        <fog attach="fog" args={["#000000", 7, 18]} />
        <CameraFit />
        <Rig>
          <Core />
          <LessonField />
          <OrbitRing />
          <Agents labelRefs={labelRefs} onEvent={onEvent} reduced={reduced} />
        </Rig>
      </Canvas>
    </div>
  );
};
