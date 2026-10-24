// Web-ready interviewer avatar: correct alpha modes, warm skin + dark hair tint,
// WebP textures, Meshopt compression. Usage: node postprocess.mjs in.glb out.glb
import { NodeIO } from '@gltf-transform/core';
import { ALL_EXTENSIONS } from '@gltf-transform/extensions';
import { dedup, meshopt, prune, textureCompress } from '@gltf-transform/functions';
import { MeshoptEncoder } from 'meshoptimizer';
import sharp from 'sharp';

const [, , input, output] = process.argv;
const io = new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({ 'meshopt.encoder': MeshoptEncoder });
const doc = await io.read(input);

// baseColorFactor multiplies the *linear* texture, so an sRGB multiplier m is m^2.2.
const lin = (rgb) => [...rgb.map((v) => v ** 2.2), 1];
const SKIN = lin([0.80, 0.63, 0.52]);   // warm medium-brown
const HAIR = lin([0.34, 0.27, 0.23]);   // dark brown

for (const m of doc.getRoot().listMaterials()) {
  const name = m.getName();
  const isHair = /ponytail|hair|bob0|short0|long0|braid|afro/i.test(name);
  if (isHair || /eyebrow|eyelash/i.test(name)) {
    // 0.5 keeps the light, semi-transparent strand tips from showing as a white fringe.
    m.setAlphaMode('MASK').setAlphaCutoff(isHair ? 0.5 : 0.45).setDoubleSided(true);
    // Light hair textures (ponytail, long01) and brows get darkened; bob01 is already dark.
    if (/ponytail|long0|eyebrow/i.test(name)) m.setBaseColorFactor(HAIR);
  } else if (/high-poly|low-poly|eye/i.test(name)) {
    // The eye mesh includes a cornea shell that must be cut out, or it hides the iris.
    m.setAlphaMode('MASK').setAlphaCutoff(0.5);
  } else {
    m.setAlphaMode('OPAQUE');
  }
  if (/\.body$/.test(name)) m.setBaseColorFactor(SKIN);
  console.log(name, m.getAlphaMode(), m.getBaseColorFactor().map((v) => v.toFixed(3)).join(','));
}

await doc.transform(
  prune(),
  dedup(),
  // Skin keeps 2048px (the face fills the frame); everything else 1024px.
  textureCompress({ encoder: sharp, targetFormat: 'webp', quality: 82, resize: [2048, 2048], pattern: /lightskinned|skin/i }),
  textureCompress({ encoder: sharp, targetFormat: 'webp', quality: 80, resize: [1024, 1024], pattern: /^(?!.*(lightskinned|skin)).*$/i }),
  meshopt({ encoder: MeshoptEncoder, level: 'medium' }),
);
await io.write(output, doc);
console.log('written', output);
