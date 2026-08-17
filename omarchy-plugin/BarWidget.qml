import QtQuick
import Quickshell
import Quickshell.Io
import qs.Ui
import qs.Commons

// Voxtype presets bar widget.
//
// Left click cycles to the next preset, right click opens the GTK4 preset
// manager (a standalone popup, not a Quickshell panel). The active preset
// name is streamed from the same kind of follow-process the built-in
// Dictation indicator uses, so every bar instance updates live.

BarWidget {
  id: root
  moduleName: "io.github.kkosu.voxtype-presets"

  property string presetName: ""
  property string presetModel: ""
  property string presetLanguage: ""

  readonly property string labelText: presetName !== "" ? ("󰍬 " + presetName) : "󰍬"

  function applyState(raw) {
    var data = Util.parseModuleJson(raw)
    if (!data) return
    presetName = String(data.name || "")
    presetModel = String(data.model || "")
    presetLanguage = String(data.language || "")
  }

  Process {
    command: ["bash", "-c", "exec \"$HOME/.local/bin/omarchy-voxtype-presets\" watch"]
    running: true
    stdout: SplitParser {
      onRead: function(data) { root.applyState(data) }
    }
  }

  implicitWidth: Math.max(Style.space(30), label.implicitWidth + Style.space(2))
  implicitHeight: barSize

  Text {
    id: label
    anchors.centerIn: parent
    text: root.labelText
    font.family: Style.fontFamily
    font.pixelSize: Style.font.caption
    color: root.bar ? root.bar.barForeground : Color.foreground
  }

  MouseArea {
    anchors.fill: parent
    acceptedButtons: Qt.LeftButton | Qt.RightButton
    cursorShape: Qt.PointingHandCursor
    onClicked: function(mouse) {
      if (mouse.button === Qt.RightButton) {
        Util.execDetached("\"$HOME/.local/bin/omarchy-voxtype-presets\" gui")
      } else {
        Util.execDetached("\"$HOME/.local/bin/omarchy-voxtype-presets\" cycle")
      }
    }
    onEntered: if (root.bar) root.bar.showTooltip(root, "Voxtype presets\nLeft click: cycle · Right click: manage")
    onExited: if (root.bar) root.bar.hideTooltip(root)
  }
}
