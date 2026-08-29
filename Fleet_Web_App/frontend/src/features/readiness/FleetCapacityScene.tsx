import { useEffect, useRef } from 'react'
import * as THREE from 'three'
import type { ReadinessCapacityModel } from './readinessCapacity'

interface FleetCapacitySceneProps {
  capacity: ReadinessCapacityModel
  onReady: () => void
  onUnavailable: () => void
}

const MAX_VISIBLE_UNITS = 40

function addBox(
  scene: THREE.Scene,
  geometry: THREE.BoxGeometry,
  material: THREE.Material,
  position: [number, number, number],
  scale: [number, number, number],
) {
  const mesh = new THREE.Mesh(geometry, material)
  mesh.position.set(...position)
  mesh.scale.set(...scale)
  scene.add(mesh)
}

function disposeScene(scene: THREE.Scene) {
  const geometries = new Set<THREE.BufferGeometry>()
  const materials = new Set<THREE.Material>()

  scene.traverse((object) => {
    if (!(object instanceof THREE.Mesh)) return
    geometries.add(object.geometry)
    const meshMaterials = Array.isArray(object.material) ? object.material : [object.material]
    meshMaterials.forEach((material) => materials.add(material))
  })

  geometries.forEach((geometry) => geometry.dispose())
  materials.forEach((material) => material.dispose())
}

export default function FleetCapacityScene({ capacity, onReady, onUnavailable }: FleetCapacitySceneProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const context = canvas.getContext('webgl2', { antialias: true, alpha: true })
      ?? canvas.getContext('webgl', { antialias: true, alpha: true })
    if (!context) {
      onUnavailable()
      return
    }

    let renderer: THREE.WebGLRenderer
    try {
      renderer = new THREE.WebGLRenderer({
        canvas,
        context,
        antialias: true,
        alpha: true,
        powerPreference: 'low-power',
      })
    } catch {
      onUnavailable()
      return
    }

    const scene = new THREE.Scene()
    scene.background = new THREE.Color('#f8fafc')

    const camera = new THREE.OrthographicCamera(-8, 8, 6, -6, 0.1, 100)
    camera.position.set(12, 12, 14)
    camera.lookAt(0, 0, 0)

    scene.add(new THREE.HemisphereLight('#ffffff', '#94a3b8', 2.4))
    const keyLight = new THREE.DirectionalLight('#ffffff', 2.2)
    keyLight.position.set(8, 14, 10)
    scene.add(keyLight)

    const unitGeometry = new THREE.BoxGeometry(1, 1, 1)
    const deckMaterial = new THREE.MeshStandardMaterial({ color: '#dbe4ee', roughness: 0.88 })
    const slotMaterial = new THREE.MeshStandardMaterial({ color: '#ffffff', roughness: 0.8 })
    const readyMaterial = new THREE.MeshStandardMaterial({ color: '#16a34a', roughness: 0.62 })
    const warningMaterial = new THREE.MeshStandardMaterial({ color: '#f59e0b', roughness: 0.62 })
    const gapMaterial = new THREE.MeshStandardMaterial({ color: '#ef4444', wireframe: true })
    const serviceMaterial = new THREE.MeshStandardMaterial({ color: '#64748b', roughness: 0.75 })
    const serviceTopMaterial = new THREE.MeshStandardMaterial({ color: '#dc2626', roughness: 0.65 })

    const requiredVisible = Math.min(capacity.required, MAX_VISIBLE_UNITS)
    const blockedVisible = Math.min(capacity.blocked, MAX_VISIBLE_UNITS)
    const columns = Math.max(1, Math.min(10, requiredVisible || 1))
    const rows = Math.max(1, Math.ceil(requiredVisible / columns))
    const width = Math.max(8, columns * 1.35)
    const depth = Math.max(5.5, rows * 1.45 + (blockedVisible > 0 ? 2.2 : 0))

    addBox(scene, unitGeometry, deckMaterial, [0, -0.35, 0], [width + 1.4, 0.45, depth + 1.2])

    const filledVisible = Math.min(capacity.eligible, requiredVisible)
    const warningVisible = Math.min(capacity.warning, filledVisible)
    const readyVisible = filledVisible - warningVisible
    const xOffset = ((columns - 1) * 1.25) / 2

    for (let index = 0; index < requiredVisible; index += 1) {
      const row = Math.floor(index / columns)
      const column = index % columns
      const x = column * 1.25 - xOffset
      const z = row * 1.35 - ((rows - 1) * 1.35) / 2 - (blockedVisible > 0 ? 0.7 : 0)
      const material = index < readyVisible
        ? readyMaterial
        : index < filledVisible
          ? warningMaterial
          : gapMaterial

      addBox(scene, unitGeometry, slotMaterial, [x, 0.02, z], [0.92, 0.08, 0.92])
      addBox(scene, unitGeometry, material, [x, 0.43, z], [0.72, 0.72, 0.72])
    }

    if (blockedVisible > 0) {
      const serviceColumns = Math.min(columns, blockedVisible)
      const serviceOffset = ((serviceColumns - 1) * 0.78) / 2
      const serviceZ = depth / 2 - 0.75
      for (let index = 0; index < blockedVisible; index += 1) {
        const column = index % serviceColumns
        const serviceRow = Math.floor(index / serviceColumns)
        const x = column * 0.78 - serviceOffset
        const z = serviceZ - serviceRow * 0.72
        addBox(scene, unitGeometry, serviceMaterial, [x, 0.25, z], [0.5, 0.45, 0.5])
        addBox(scene, unitGeometry, serviceTopMaterial, [x, 0.53, z], [0.52, 0.1, 0.52])
      }
    }

    let frame = 0
    const render = () => {
      frame = 0
      renderer.render(scene, camera)
    }

    const resize = () => {
      const bounds = canvas.getBoundingClientRect()
      const renderWidth = Math.max(1, Math.round(bounds.width))
      const renderHeight = Math.max(1, Math.round(bounds.height))
      const aspect = renderWidth / renderHeight
      const viewHeight = Math.max(8, depth * 1.05)
      camera.left = -(viewHeight * aspect) / 2
      camera.right = (viewHeight * aspect) / 2
      camera.top = viewHeight / 2
      camera.bottom = -viewHeight / 2
      camera.updateProjectionMatrix()
      renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5))
      renderer.setSize(renderWidth, renderHeight, false)
      render()
    }

    const requestRender = () => {
      if (document.hidden || frame) return
      frame = window.requestAnimationFrame(render)
    }
    const handleVisibility = () => {
      if (!document.hidden) requestRender()
    }
    const handleContextLost = (event: Event) => {
      event.preventDefault()
      onUnavailable()
    }

    canvas.addEventListener('webglcontextlost', handleContextLost)
    document.addEventListener('visibilitychange', handleVisibility)

    const resizeObserver = typeof ResizeObserver === 'undefined' ? null : new ResizeObserver(resize)
    resizeObserver?.observe(canvas)
    window.addEventListener('resize', resize)
    resize()
    onReady()

    return () => {
      if (frame) window.cancelAnimationFrame(frame)
      resizeObserver?.disconnect()
      window.removeEventListener('resize', resize)
      document.removeEventListener('visibilitychange', handleVisibility)
      canvas.removeEventListener('webglcontextlost', handleContextLost)
      renderer.setAnimationLoop(null)
      disposeScene(scene)
      renderer.dispose()
    }
  }, [capacity, onReady, onUnavailable])

  return (
    <canvas
      aria-hidden="true"
      className="block h-full w-full"
      data-testid="capacity-three-scene"
      ref={canvasRef}
      tabIndex={-1}
    />
  )
}
