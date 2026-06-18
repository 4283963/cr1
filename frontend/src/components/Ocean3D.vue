<template>
  <div ref="containerRef" class="ocean-3d-container">
    <div class="tooltip" v-if="hoveredCage" :style="tooltipStyle">
      <div class="tooltip-title">{{ hoveredCage.name }}</div>
      <div>温度: {{ hoveredCage.temperature }}°C</div>
      <div>盐度: {{ hoveredCage.salinity }}‰</div>
      <div>深度: {{ hoveredCage.depth }}m</div>
      <div class="tooltip-hint">点击查看详情</div>
    </div>
    <div class="controls-hint">
      <span>🖱️ 左键拖动旋转</span>
      <span>🔍 滚轮缩放</span>
      <span>⇧ 右键平移</span>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'

const props = defineProps({
  cages: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['cage-click'])

const containerRef = ref(null)
const hoveredCage = ref(null)
const tooltipStyle = ref({ left: '0px', top: '0px' })

let scene, camera, renderer, controls, raycaster, mouse
let cageMeshes = new Map()
let animationId = null
let waterSurface = null
let sharedGeometries = null
let sharedMaterials = null
let onMouseMoveHandler = null
let onClickHandler = null
let onResizeHandler = null

const statusColors = {
  normal: 0x4caf50,
  warning: 0xff9800,
  error: 0xf44336
}

const initSharedResources = () => {
  const cageWidth = 8
  const cageHeight = 4
  const cageDepth = 8

  sharedGeometries = {
    frame: new THREE.BoxGeometry(cageWidth, cageHeight, cageDepth),
    net: new THREE.BoxGeometry(cageWidth - 0.2, cageHeight - 0.2, cageDepth - 0.2),
    buoy: new THREE.CylinderGeometry(0.5, 0.6, 1.5, 8),
    rope: new THREE.CylinderGeometry(0.05, 0.05, 5, 4),
    sensor: new THREE.SphereGeometry(0.6, 16, 16)
  }

  sharedMaterials = {
    rope: new THREE.MeshBasicMaterial({ color: 0x78909c }),
    sensor: new THREE.MeshStandardMaterial({
      color: 0x2196f3,
      emissive: 0x2196f3,
      emissiveIntensity: 0.5
    }),
    frameNormal: createFrameMaterial('normal'),
    frameWarning: createFrameMaterial('warning'),
    frameError: createFrameMaterial('error'),
    netNormal: createNetMaterial('normal'),
    netWarning: createNetMaterial('warning'),
    netError: createNetMaterial('error'),
    buoyNormal: createBuoyMaterial('normal'),
    buoyWarning: createBuoyMaterial('warning'),
    buoyError: createBuoyMaterial('error')
  }
}

const createFrameMaterial = (status) => new THREE.LineBasicMaterial({
  color: statusColors[status] || 0x4caf50,
  transparent: true,
  opacity: 0.9
})

const createNetMaterial = (status) => new THREE.MeshBasicMaterial({
  color: statusColors[status] || 0x4caf50,
  transparent: true,
  opacity: 0.15,
  side: THREE.DoubleSide,
  wireframe: true
})

const createBuoyMaterial = (status) => new THREE.MeshStandardMaterial({
  color: statusColors[status] || 0x4caf50,
  emissive: statusColors[status] || 0x4caf50,
  emissiveIntensity: 0.3
})

const getStatusMaterial = (type, status) => {
  const key = `${type}${status.charAt(0).toUpperCase() + status.slice(1)}`
  return sharedMaterials[key] || sharedMaterials[`${type}Normal`]
}

const disposeMesh = (object) => {
  if (!object) return

  object.traverse((child) => {
    if (child.geometry) {
      child.geometry.dispose()
    }
    if (child.material) {
      if (Array.isArray(child.material)) {
        child.material.forEach(m => m.dispose())
      } else {
        child.material.dispose()
      }
    }
  })
}

const disposeAllCages = () => {
  cageMeshes.forEach((mesh) => {
    scene.remove(mesh)
    disposeMesh(mesh)
  })
  cageMeshes.clear()
}

const createCageMesh = (cageData) => {
  const group = new THREE.Group()

  const frameGeo = new THREE.EdgesGeometry(sharedGeometries.frame)
  const frameMat = getStatusMaterial('frame', cageData.status)
  const frame = new THREE.LineSegments(frameGeo, frameMat)
  group.add(frame)

  const netMat = getStatusMaterial('net', cageData.status)
  const net = new THREE.Mesh(sharedGeometries.net, netMat)
  group.add(net)

  const buoyMat = getStatusMaterial('buoy', cageData.status)
  const cageWidth = 8
  const cageHeight = 4
  const cageDepth = 8

  const buoyPositions = [
    [-cageWidth / 2 + 1, cageHeight / 2 + 0.75, -cageDepth / 2 + 1],
    [cageWidth / 2 - 1, cageHeight / 2 + 0.75, -cageDepth / 2 + 1],
    [-cageWidth / 2 + 1, cageHeight / 2 + 0.75, cageDepth / 2 - 1],
    [cageWidth / 2 - 1, cageHeight / 2 + 0.75, cageDepth / 2 - 1]
  ]

  buoyPositions.forEach(pos => {
    const buoy = new THREE.Mesh(sharedGeometries.buoy, buoyMat)
    buoy.position.set(pos[0], pos[1], pos[2])
    buoy.castShadow = true
    group.add(buoy)
  })

  for (let i = 0; i < 2; i++) {
    const rope = new THREE.Mesh(sharedGeometries.rope, sharedMaterials.rope)
    rope.position.set(
      (i === 0 ? -1 : 1) * (cageWidth / 2 - 1),
      cageHeight / 2 + 3.25,
      -cageDepth / 2 + 1
    )
    group.add(rope)
  }

  const sensor = new THREE.Mesh(sharedGeometries.sensor, sharedMaterials.sensor)
  sensor.position.set(0, -cageHeight / 2 - 0.5, 0)
  group.add(sensor)

  const groundY = -20
  const cageY = groundY + cageData.depth + cageHeight / 2
  group.position.set(cageData.x, cageY, cageData.z)

  group.userData = {
    cageId: cageData.id,
    cageData: { ...cageData }
  }

  return group
}

const createCages = () => {
  disposeAllCages()

  props.cages.forEach(cageData => {
    const mesh = createCageMesh(cageData)
    scene.add(mesh)
    cageMeshes.set(cageData.id, mesh)
  })
}

const updateCageData = () => {
  const idSet = new Set(props.cages.map(c => c.id))
  const existingIds = new Set(cageMeshes.keys())

  const needRebuild =
    idSet.size !== existingIds.size ||
    [...idSet].some(id => !existingIds.has(id))

  if (needRebuild) {
    createCages()
    return
  }

  props.cages.forEach(cageData => {
    const mesh = cageMeshes.get(cageData.id)
    if (!mesh) return

    mesh.userData.cageData = { ...cageData }

    mesh.traverse((child) => {
      if (child === mesh) return

      if (child.material && child.material.color) {
        const targetColor = statusColors[cageData.status] || 0x4caf50
        if (child.geometry === sharedGeometries.net ||
            child.geometry === sharedGeometries.buoy) {
          child.material.color.setHex(targetColor)
          if (child.material.emissive) {
            child.material.emissive.setHex(targetColor)
          }
        }
      }
    })
  })
}

const initScene = () => {
  const container = containerRef.value
  const width = container.clientWidth
  const height = container.clientHeight

  scene = new THREE.Scene()
  scene.background = new THREE.Color(0x0a1628)
  scene.fog = new THREE.Fog(0x0a1628, 80, 200)

  camera = new THREE.PerspectiveCamera(60, width / height, 0.1, 1000)
  camera.position.set(60, 50, 80)

  renderer = new THREE.WebGLRenderer({ antialias: true })
  renderer.setSize(width, height)
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
  renderer.shadowMap.enabled = true
  container.appendChild(renderer.domElement)

  controls = new OrbitControls(camera, renderer.domElement)
  controls.enableDamping = true
  controls.dampingFactor = 0.05
  controls.maxPolarAngle = Math.PI / 2.1
  controls.minDistance = 20
  controls.maxDistance = 150

  raycaster = new THREE.Raycaster()
  mouse = new THREE.Vector2()

  initSharedResources()

  addLights()
  addSeabed()
  addWaterSurface()
  addGrid()
  addDepthMarkers()
  createCages()

  animate()

  onMouseMoveHandler = (e) => onMouseMove(e)
  onClickHandler = (e) => onMouseClick(e)
  onResizeHandler = () => onWindowResize()

  renderer.domElement.addEventListener('mousemove', onMouseMoveHandler)
  renderer.domElement.addEventListener('click', onClickHandler)
  window.addEventListener('resize', onResizeHandler)
}

const addLights = () => {
  const ambientLight = new THREE.AmbientLight(0x4fc3f7, 0.4)
  scene.add(ambientLight)

  const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8)
  directionalLight.position.set(50, 100, 50)
  directionalLight.castShadow = true
  directionalLight.shadow.mapSize.width = 1024
  directionalLight.shadow.mapSize.height = 1024
  directionalLight.shadow.camera.near = 0.5
  directionalLight.shadow.camera.far = 500
  directionalLight.shadow.camera.left = -100
  directionalLight.shadow.camera.right = 100
  directionalLight.shadow.camera.top = 100
  directionalLight.shadow.camera.bottom = -100
  scene.add(directionalLight)

  const pointLight = new THREE.PointLight(0x4fc3f7, 0.5, 100)
  pointLight.position.set(0, 30, 0)
  scene.add(pointLight)
}

const addSeabed = () => {
  const geometry = new THREE.PlaneGeometry(200, 200, 50, 50)
  const positions = geometry.attributes.position
  for (let i = 0; i < positions.count; i++) {
    const x = positions.getX(i)
    const y = positions.getY(i)
    const z = Math.sin(x * 0.05) * Math.cos(y * 0.05) * 2
    positions.setZ(i, z)
  }
  geometry.computeVertexNormals()

  const material = new THREE.MeshStandardMaterial({
    color: 0x2d5a3d,
    roughness: 0.9,
    metalness: 0.1,
    flatShading: true
  })

  const seabed = new THREE.Mesh(geometry, material)
  seabed.rotation.x = -Math.PI / 2
  seabed.position.y = -25
  seabed.receiveShadow = true
  scene.add(seabed)
}

const addWaterSurface = () => {
  const geometry = new THREE.PlaneGeometry(300, 300)
  const material = new THREE.MeshPhongMaterial({
    color: 0x00bcd4,
    transparent: true,
    opacity: 0.3,
    side: THREE.DoubleSide,
    shininess: 100
  })

  waterSurface = new THREE.Mesh(geometry, material)
  waterSurface.rotation.x = -Math.PI / 2
  waterSurface.position.y = 5
  scene.add(waterSurface)
}

const addGrid = () => {
  const gridHelper = new THREE.GridHelper(100, 20, 0x00acc1, 0x006064)
  gridHelper.position.y = -20
  scene.add(gridHelper)

  const axesHelper = new THREE.AxesHelper(15)
  axesHelper.position.set(-45, -19.5, -45)
  scene.add(axesHelper)
}

const addDepthMarkers = () => {
  for (let depth = 5; depth <= 20; depth += 5) {
    const geometry = new THREE.RingGeometry(0.3, 0.8, 16)
    const material = new THREE.MeshBasicMaterial({
      color: 0x4fc3f7,
      transparent: true,
      opacity: 0.5,
      side: THREE.DoubleSide
    })
    const marker = new THREE.Mesh(geometry, material)
    marker.rotation.x = -Math.PI / 2
    marker.position.set(-48, -depth, -48)
    scene.add(marker)
  }
}

const animate = () => {
  animationId = requestAnimationFrame(animate)
  controls.update()

  if (waterSurface) {
    waterSurface.position.y = 5 + Math.sin(Date.now() * 0.001) * 0.3
  }

  renderer.render(scene, camera)
}

const onMouseMove = (event) => {
  if (!containerRef.value || !cageMeshes.size) return

  const rect = containerRef.value.getBoundingClientRect()
  mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1
  mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1

  tooltipStyle.value = {
    left: event.clientX - rect.left + 15 + 'px',
    top: event.clientY - rect.top + 15 + 'px'
  }

  raycaster.setFromCamera(mouse, camera)
  const meshes = []
  cageMeshes.forEach(m => meshes.push(...m.children))
  const intersects = raycaster.intersectObjects(meshes, true)

  if (intersects.length > 0) {
    let obj = intersects[0].object
    while (obj.parent && !obj.userData.cageData) {
      obj = obj.parent
    }
    if (obj.userData.cageData) {
      hoveredCage.value = obj.userData.cageData
      document.body.style.cursor = 'pointer'
    } else {
      hoveredCage.value = null
      document.body.style.cursor = 'default'
    }
  } else {
    hoveredCage.value = null
    document.body.style.cursor = 'default'
  }
}

const onMouseClick = () => {
  if (hoveredCage.value) {
    emit('cage-click', hoveredCage.value)
  }
}

const onWindowResize = () => {
  if (!containerRef.value || !camera || !renderer) return
  const container = containerRef.value
  const width = container.clientWidth
  const height = container.clientHeight

  camera.aspect = width / height
  camera.updateProjectionMatrix()
  renderer.setSize(width, height)
}

watch(() => props.cages, () => {
  if (scene && props.cages.length > 0) {
    updateCageData()
  }
})

onMounted(() => {
  initScene()
})

onUnmounted(() => {
  if (animationId) {
    cancelAnimationFrame(animationId)
    animationId = null
  }

  if (onMouseMoveHandler && renderer) {
    renderer.domElement.removeEventListener('mousemove', onMouseMoveHandler)
    onMouseMoveHandler = null
  }
  if (onClickHandler && renderer) {
    renderer.domElement.removeEventListener('click', onClickHandler)
    onClickHandler = null
  }
  if (onResizeHandler) {
    window.removeEventListener('resize', onResizeHandler)
    onResizeHandler = null
  }

  disposeAllCages()

  if (sharedGeometries) {
    Object.values(sharedGeometries).forEach(g => g.dispose())
    sharedGeometries = null
  }
  if (sharedMaterials) {
    Object.values(sharedMaterials).forEach(m => m.dispose())
    sharedMaterials = null
  }

  if (controls) {
    controls.dispose()
    controls = null
  }

  if (renderer) {
    renderer.dispose()
    if (containerRef.value && renderer.domElement) {
      containerRef.value.removeChild(renderer.domElement)
    }
    renderer = null
  }

  scene = null
  camera = null
  raycaster = null
  mouse = null
  waterSurface = null

  document.body.style.cursor = 'default'
})
</script>

<style scoped>
.ocean-3d-container {
  width: 100%;
  height: 100%;
  position: relative;
  overflow: hidden;
}

.tooltip {
  position: absolute;
  background: rgba(0, 20, 40, 0.95);
  color: #fff;
  padding: 10px 14px;
  border-radius: 6px;
  font-size: 12px;
  pointer-events: none;
  z-index: 100;
  border: 1px solid rgba(79, 195, 247, 0.5);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  line-height: 1.6;
}

.tooltip-title {
  font-weight: 600;
  color: #4fc3f7;
  margin-bottom: 4px;
  font-size: 13px;
}

.tooltip-hint {
  margin-top: 6px;
  color: #ffeb3b;
  font-size: 11px;
}

.controls-hint {
  position: absolute;
  bottom: 12px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  gap: 20px;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.5);
  background: rgba(0, 20, 40, 0.6);
  padding: 6px 16px;
  border-radius: 20px;
  pointer-events: none;
}
</style>
