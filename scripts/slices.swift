// Dynamic-wallpaper thumbnail: each image (e.g. dawn, day, dusk, night) fills the frame and
// shows through one diagonal strip, like the previews in System Settings.
// Usage: slices <out.jpg> <width> <height> <image>...
import Foundation
import ImageIO
import UniformTypeIdentifiers

let args = CommandLine.arguments
guard args.count >= 5, let w = Int(args[2]), let h = Int(args[3]) else {
    FileHandle.standardError.write("usage: slices out.jpg width height image...\n".data(using: .utf8)!)
    exit(1)
}
let images = args[4...].map { path -> CGImage in
    guard let src = CGImageSourceCreateWithURL(URL(fileURLWithPath: path) as CFURL, nil),
          let img = CGImageSourceCreateImageAtIndex(src, 0, nil) else {
        FileHandle.standardError.write("can't read \(path)\n".data(using: .utf8)!)
        exit(1)
    }
    return img
}

let W = CGFloat(w), H = CGFloat(h), slant = H * 0.6
let ctx = CGContext(data: nil, width: w, height: h, bitsPerComponent: 8, bytesPerRow: 0,
                    space: CGColorSpace(name: CGColorSpace.sRGB)!, bitmapInfo: CGImageAlphaInfo.noneSkipLast.rawValue)!
ctx.interpolationQuality = .high
let n = images.count
for (i, img) in images.enumerated() {
    // Strip edges lean like "/": the outer strips run past the canvas
    let left = i == 0 ? -W : W * CGFloat(i) / CGFloat(n)
    let right = i == n - 1 ? 2 * W : W * CGFloat(i + 1) / CGFloat(n)
    let strip = CGMutablePath()
    strip.addLines(between: [CGPoint(x: left - slant / 2, y: 0), CGPoint(x: right - slant / 2, y: 0),
                             CGPoint(x: right + slant / 2, y: H), CGPoint(x: left + slant / 2, y: H)])
    ctx.saveGState()
    ctx.addPath(strip)
    ctx.clip()
    let scale = max(W / CGFloat(img.width), H / CGFloat(img.height)) // aspect fill
    let dw = CGFloat(img.width) * scale, dh = CGFloat(img.height) * scale
    ctx.draw(img, in: CGRect(x: (W - dw) / 2, y: (H - dh) / 2, width: dw, height: dh))
    ctx.restoreGState()
}

let dest = CGImageDestinationCreateWithURL(URL(fileURLWithPath: args[1]) as CFURL, UTType.jpeg.identifier as CFString, 1, nil)!
CGImageDestinationAddImage(dest, ctx.makeImage()!, [kCGImageDestinationLossyCompressionQuality: 0.8] as CFDictionary)
guard CGImageDestinationFinalize(dest) else { exit(1) }
