import { useEffect, useRef } from "react";
import { Animated, Easing, StyleSheet, Text, View } from "react-native";

import { Mark } from "../components/Logo";
import { color, space, type } from "../theme";

export function BootScreen() {
  const enter = useRef(new Animated.Value(0)).current;
  const sweep = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.timing(enter, {
      toValue: 1,
      duration: 460,
      easing: Easing.out(Easing.cubic),
      useNativeDriver: true,
    }).start();

    Animated.loop(
      Animated.sequence([
        Animated.timing(sweep, {
          toValue: 1,
          duration: 1100,
          easing: Easing.inOut(Easing.quad),
          useNativeDriver: true,
        }),
        Animated.timing(sweep, {
          toValue: 0,
          duration: 0,
          useNativeDriver: true,
        }),
      ]),
    ).start();
  }, [enter, sweep]);

  return (
    <View style={styles.root}>
      <Animated.View
        style={{
          opacity: enter,
          transform: [
            { scale: enter.interpolate({ inputRange: [0, 1], outputRange: [0.86, 1] }) },
          ],
        }}
      >
        <Mark size={100} tint="#FFFFFF" accent="#7FC5D2" />
      </Animated.View>

      <Animated.View style={[styles.words, { opacity: enter }]}>
        <View style={styles.lockup}>
          <Text style={styles.wordmark}>Bharosa</Text>
          <Text style={styles.role}>Consign</Text>
        </View>
        <Text style={styles.tagline}>Record every movement</Text>
      </Animated.View>

      <View style={styles.track}>
        <Animated.View
          style={[
            styles.runner,
            {
              opacity: sweep.interpolate({
                inputRange: [0, 0.15, 0.85, 1],
                outputRange: [0, 1, 1, 0],
              }),
              transform: [
                {
                  translateX: sweep.interpolate({
                    inputRange: [0, 1],
                    outputRange: [0, 116],
                  }),
                },
              ],
            },
          ]}
        />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: color.ledger,
    alignItems: "center",
    justifyContent: "center",
    gap: space.xl,
  },
  words: { alignItems: "center", gap: 6 },
  lockup: { flexDirection: "row", alignItems: "baseline", gap: 7 },
  wordmark: {
    fontSize: type.headline,
    fontWeight: "700",
    letterSpacing: -0.7,
    color: "#FFFFFF",
  },
  role: {
    fontSize: type.headline * 0.86,
    fontWeight: "400",
    letterSpacing: -0.3,
    color: "#7FC5D2",
  },
  tagline: {
    fontSize: type.body,
    fontWeight: "500",
    color: "#9FBEC6",
    letterSpacing: 0.2,
  },
  track: {
    position: "absolute",
    bottom: space.huge,
    width: 140,
    height: 3,
    borderRadius: 2,
    backgroundColor: "rgba(255,255,255,0.14)",
    overflow: "hidden",
  },
  runner: {
    width: 24,
    height: 3,
    borderRadius: 2,
    backgroundColor: "#7FC5D2",
  },
});
