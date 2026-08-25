import { useEffect, useRef } from "react";
import { Animated, Easing, StyleSheet, Text, View } from "react-native";

import { Mark } from "../components/Logo";
import { color, space, type } from "../theme";

export function BootScreen() {
  const enter = useRef(new Animated.Value(0)).current;
  const pulse = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.timing(enter, {
      toValue: 1,
      duration: 520,
      easing: Easing.out(Easing.cubic),
      useNativeDriver: true,
    }).start();

    Animated.loop(
      Animated.sequence([
        Animated.timing(pulse, {
          toValue: 1,
          duration: 900,
          easing: Easing.inOut(Easing.quad),
          useNativeDriver: true,
        }),
        Animated.timing(pulse, {
          toValue: 0,
          duration: 900,
          easing: Easing.inOut(Easing.quad),
          useNativeDriver: true,
        }),
      ]),
    ).start();
  }, [enter, pulse]);

  return (
    <View style={styles.root}>
      <Animated.View
        style={{
          opacity: enter,
          transform: [
            { scale: enter.interpolate({ inputRange: [0, 1], outputRange: [0.82, 1] }) },
          ],
        }}
      >
        <Mark size={104} tint="#FFFFFF" accent="#8FD8BC" />
      </Animated.View>

      <Animated.View style={[styles.words, { opacity: enter }]}>
        <Text style={styles.wordmark}>Bharosa</Text>
        <Text style={styles.tagline}>Check before you use it</Text>
      </Animated.View>

      <Animated.View
        style={[
          styles.dot,
          { opacity: pulse.interpolate({ inputRange: [0, 1], outputRange: [0.25, 0.9] }) },
        ]}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: color.pine,
    alignItems: "center",
    justifyContent: "center",
    gap: space.xl,
  },
  words: { alignItems: "center", gap: 6 },
  wordmark: {
    fontSize: type.headline,
    fontWeight: "800",
    letterSpacing: -0.8,
    color: "#FFFFFF",
  },
  tagline: {
    fontSize: type.body,
    fontWeight: "500",
    color: "#A9C8BC",
    letterSpacing: 0.2,
  },
  dot: {
    position: "absolute",
    bottom: space.huge,
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: "#8FD8BC",
  },
});
