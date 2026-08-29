import { useEffect, useMemo, useRef, useState } from 'react'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { cargoBayDimensions, cargoParcelDetail } from '../features/loadOptimization/cargoBay'
import type { VirtualLoad } from '../features/loadOptimization/types'

const COLORS = ['#2563eb', '#059669', '#f59e0b', '#dc2626', '#7c3aed', '#0891b2']

export function CargoBay3D({ load }: { load: VirtualLoad | null }) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [hoveredParcel, setHoveredParcel] = useState<{ loadId: string; parcelId: string } | null>(null)
  const [selectedParcel, setSelectedParcel] = useState<{ loadId: string; parcelId: string } | null>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas || !load) return
    const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true, powerPreference: 'low-power' })
    renderer.outputColorSpace = THREE.SRGBColorSpace
    renderer.shadowMap.enabled = true
    renderer.shadowMap.type = THREE.PCFSoftShadowMap
    const scene = new THREE.Scene()
    scene.background = new THREE.Color('#eef4fb')
    scene.fog = new THREE.Fog('#eef4fb', 18, 35)
    const camera = new THREE.PerspectiveCamera(38, 1, 0.1, 100)
    camera.position.set(11.5, 8.5, 13.5)
    camera.lookAt(0, 1.5, 0)
    const controls = new OrbitControls(camera, canvas)
    controls.enableDamping = true
    controls.dampingFactor = 0.06
    controls.minDistance = 7
    controls.maxDistance = 26
    controls.maxPolarAngle = Math.PI * 0.48
    controls.target.set(0, 1.4, 0)
    scene.add(new THREE.HemisphereLight('#ffffff', '#64748b', 2.7))
    const light = new THREE.DirectionalLight('#ffffff', 3.4)
    light.position.set(7, 14, 9)
    light.castShadow = true
    scene.add(light)

    const dimensions = cargoBayDimensions(load)
    const maxX = dimensions.lengthCm
    const maxY = dimensions.widthCm
    const maxZ = dimensions.heightCm
    const scale = 9 / Math.max(maxX, maxY, maxZ)
    const unit = new THREE.BoxGeometry(1, 1, 1)
    const floor = new THREE.Mesh(unit, new THREE.MeshStandardMaterial({ color: '#cbd5e1', roughness: 0.82, metalness: 0.12 }))
    floor.position.set(0, -0.08, 0)
    floor.scale.set(maxX * scale, 0.12, maxY * scale)
    floor.receiveShadow = true
    scene.add(floor)

    const grid = new THREE.GridHelper(Math.max(maxX, maxY) * scale, 14, '#64748b', '#cbd5e1')
    grid.position.y = 0.005
    scene.add(grid)

    const bayOutline = new THREE.Mesh(
      new THREE.BoxGeometry(maxX * scale, maxZ * scale, maxY * scale),
      new THREE.MeshStandardMaterial({ color: '#2563eb', transparent: true, opacity: 0.055, side: THREE.DoubleSide }),
    )
    bayOutline.position.set(0, maxZ * scale / 2, 0)
    scene.add(bayOutline)
    const bayEdges = new THREE.LineSegments(
      new THREE.EdgesGeometry(bayOutline.geometry),
      new THREE.LineBasicMaterial({ color: '#64748b', transparent: true, opacity: 0.78 }),
    )
    bayEdges.position.copy(bayOutline.position)
    scene.add(bayEdges)

    const parcelMeshes: THREE.Mesh[] = []
    load.placements.forEach((placement, index) => {
      const color = placement.fragile ? '#ef4444' : COLORS[index % COLORS.length]
      const material = new THREE.MeshStandardMaterial({ color, roughness: 0.52, metalness: 0.05, emissive: placement.fragile ? '#3f0808' : '#000000' })
      const box = new THREE.Mesh(unit, material)
      const x = (placement.x_cm + placement.length_cm / 2 - maxX / 2) * scale
      const y = (placement.z_cm + placement.height_cm / 2) * scale
      const z = (placement.y_cm + placement.width_cm / 2 - maxY / 2) * scale
      box.position.set(x, y, z)
      box.scale.set(placement.length_cm * scale, placement.height_cm * scale, placement.width_cm * scale)
      box.castShadow = true
      box.receiveShadow = true
      box.userData.parcelId = placement.parcel_id
      box.userData.baseEmissive = material.emissive.getHex()
      scene.add(box)
      parcelMeshes.push(box)
      const edges = new THREE.LineSegments(
        new THREE.EdgesGeometry(new THREE.BoxGeometry(
          placement.length_cm * scale,
          placement.height_cm * scale,
          placement.width_cm * scale,
        )),
        new THREE.LineBasicMaterial({ color: '#ffffff', transparent: true, opacity: 0.88 }),
      )
      edges.position.set(x, y, z)
      scene.add(edges)
    })

    const raycaster = new THREE.Raycaster()
    const pointer = new THREE.Vector2()
    let selectedId: string | null = null
    let hoveredId: string | null = null
    const hitAt = (event: MouseEvent) => {
      const bounds = canvas.getBoundingClientRect()
      pointer.x = ((event.clientX - bounds.left) / Math.max(bounds.width, 1)) * 2 - 1
      pointer.y = -((event.clientY - bounds.top) / Math.max(bounds.height, 1)) * 2 + 1
      raycaster.setFromCamera(pointer, camera)
      return raycaster.intersectObjects(parcelMeshes, false)[0]?.object as THREE.Mesh | undefined
    }
    const applyHighlight = () => {
      parcelMeshes.forEach((mesh) => {
        const material = mesh.material as THREE.MeshStandardMaterial
        const parcelId = String(mesh.userData.parcelId)
        material.emissive.setHex(Number(mesh.userData.baseEmissive ?? 0))
        material.emissiveIntensity = 1
        if (parcelId === selectedId) {
          material.emissive.set('#dbeafe')
          material.emissiveIntensity = 0.85
        } else if (parcelId === hoveredId) {
          material.emissive.set('#ffffff')
          material.emissiveIntensity = 0.45
        }
      })
    }
    const handlePointerMove = (event: PointerEvent) => {
      const parcelId = String(hitAt(event)?.userData.parcelId ?? '') || null
      if (parcelId === hoveredId) return
      hoveredId = parcelId
      canvas.style.cursor = parcelId ? 'pointer' : 'grab'
      setHoveredParcel(parcelId ? { loadId: load.load_id, parcelId } : null)
      applyHighlight()
    }
    const handlePointerLeave = () => {
      hoveredId = null
      canvas.style.cursor = 'grab'
      setHoveredParcel(null)
      applyHighlight()
    }
    const handlePointerClick = (event: MouseEvent) => {
      selectedId = String(hitAt(event)?.userData.parcelId ?? '') || null
      setSelectedParcel(selectedId ? { loadId: load.load_id, parcelId: selectedId } : null)
      applyHighlight()
    }
    canvas.addEventListener('pointermove', handlePointerMove)
    canvas.addEventListener('pointerleave', handlePointerLeave)
    canvas.addEventListener('click', handlePointerClick)

    const resize = () => {
      const bounds = canvas.getBoundingClientRect()
      const width = Math.max(1, Math.round(bounds.width))
      const height = Math.max(1, Math.round(bounds.height))
      const aspect = width / height
      camera.aspect = aspect
      camera.updateProjectionMatrix()
      renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5))
      renderer.setSize(width, height, false)
    }
    const observer = new ResizeObserver(resize)
    observer.observe(canvas)
    resize()
    renderer.setAnimationLoop(() => {
      controls.update()
      renderer.render(scene, camera)
    })
    return () => {
      observer.disconnect()
      canvas.removeEventListener('pointermove', handlePointerMove)
      canvas.removeEventListener('pointerleave', handlePointerLeave)
      canvas.removeEventListener('click', handlePointerClick)
      renderer.setAnimationLoop(null)
      controls.dispose()
      renderer.dispose()
      scene.traverse((object) => {
        if (!(object instanceof THREE.Mesh || object instanceof THREE.LineSegments)) return
        object.geometry.dispose()
        const materials = Array.isArray(object.material) ? object.material : [object.material]
        materials.forEach((material) => material.dispose())
      })
    }
  }, [load])

  const dimensions = load ? cargoBayDimensions(load) : null
  const detail = useMemo(() => {
    if (!load) return null
    const focus = hoveredParcel?.loadId === load.load_id ? hoveredParcel : selectedParcel?.loadId === load.load_id ? selectedParcel : null
    return focus ? cargoParcelDetail(load, focus.parcelId) : null
  }, [hoveredParcel, load, selectedParcel])
  return <div aria-label="Cargo bay loading visualization" className="relative min-h-[380px] w-full overflow-hidden bg-[#eef4fb]">{load ? <><canvas aria-label="Interactive cargo parcels" className="absolute inset-0 h-full w-full touch-none" ref={canvasRef} tabIndex={0} /><div className="pointer-events-none absolute left-4 top-4 rounded-lg bg-white/92 px-3 py-2 text-xs font-bold text-slate-700 shadow-sm ring-1 ring-slate-200">Bay {dimensions?.lengthCm} × {dimensions?.widthCm} × {dimensions?.heightCm} cm</div>{detail && <div aria-live="polite" className="pointer-events-none absolute right-4 top-4 w-[min(230px,calc(100%-2rem))] rounded-lg border border-blue-200 bg-white/95 p-3 shadow-lg"><div className="text-[11px] font-bold uppercase text-blue-700">Parcel details</div><div className="mt-1 truncate text-sm font-black text-slate-950">{detail.parcelId}</div><dl className="mt-2 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-xs"><dt className="font-semibold text-slate-500">Size</dt><dd className="text-right font-bold text-slate-800">{detail.dimensions}</dd><dt className="font-semibold text-slate-500">Position</dt><dd className="text-right font-bold text-slate-800">{detail.position}</dd><dt className="font-semibold text-slate-500">Layer</dt><dd className="text-right font-bold text-slate-800">{detail.layer}</dd><dt className="font-semibold text-slate-500">Load order</dt><dd className="text-right font-bold text-slate-800">{detail.loadSequence ?? 'Not set'}</dd></dl><div className="mt-2 border-t border-slate-200 pt-2 text-xs font-bold text-slate-700">{detail.handling.join(' · ')}</div></div>}<div className="pointer-events-none absolute bottom-4 left-4 flex gap-3 rounded-lg bg-white/92 px-3 py-2 text-xs font-bold text-slate-700 shadow-sm ring-1 ring-slate-200"><span className="inline-flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-sm bg-blue-600" />Standard</span><span className="inline-flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-sm bg-red-500" />Fragile · top layer</span></div><div className="pointer-events-none absolute bottom-4 right-4 rounded-lg bg-slate-950/75 px-3 py-2 text-[11px] font-semibold text-white">Hover or tap a parcel · drag to rotate · scroll to zoom</div></> : <div className="absolute inset-0 grid place-items-center text-sm font-semibold text-fleet-muted">Select a virtual load to inspect placement.</div>}</div>
}
