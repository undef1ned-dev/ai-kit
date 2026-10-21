package com.example.examplemod.config;

import com.example.examplemod.ModConstants;
import net.minecraftforge.common.config.Config;

@Config(modid = ModConstants.MOD_ID)
public final class ModConfig {
    @Config.Comment("Ticks the grinder needs to process one ore")
    @Config.RangeInt(min = 1, max = 400)
    @Config.LangKey("examplemod.config.grinder.speed")
    public static int grinderTicksPerOre = 200;

    @Config.Comment("Multiplier of the grinder output")
    @Config.RangeInt(min = 1, max = 4)
    public static int grinderOutputMultiplier = 2;

    private ModConfig() {
    }
}
