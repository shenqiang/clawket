import AVFoundation
import ExpoModulesCore
import Speech

// Stub version for Mac Catalyst build (iOS 26 SpeechAnalyzer API unavailable on SDK 18.5)
// Speech recognition is not supported on macOS Catalyst. iOS builds use the full implementation.

public final class ClawketSpeechRecognitionModule: Module {
  private let resultEvent = "onSpeechResult"
  private let stateEvent = "onSpeechState"
  private let errorEvent = "onSpeechError"
  private let levelEvent = "onSpeechLevel"

  public func definition() -> ModuleDefinition {
    Name("ClawketSpeechRecognition")

    Events(resultEvent, stateEvent, errorEvent, levelEvent)

    AsyncFunction("isAvailableAsync") { (localeIdentifier: String?, promise: Promise) in
      promise.resolve(false)
    }.runOnQueue(.main)

    AsyncFunction("requestPermissionsAsync") { (promise: Promise) in
      promise.resolve(false)
    }.runOnQueue(.main)

    AsyncFunction("startAsync") { (localeIdentifier: String?, promise: Promise) in
      promise.reject("UNAVAILABLE", "Speech recognition is not available on macOS Catalyst")
    }.runOnQueue(.main)

    AsyncFunction("stopAsync") { (promise: Promise) in
      promise.resolve()
    }.runOnQueue(.main)

    AsyncFunction("isRecognitionAvailableAsync") { (localeIdentifier: String?, promise: Promise) in
      promise.resolve(false)
    }.runOnQueue(.main)
  }
}
