package com.example.examplemod;

import com.example.examplemod.network.ModNetwork;
import net.minecraftforge.fml.common.Mod;
import net.minecraftforge.fml.common.event.FMLPreInitializationEvent;
import org.apache.logging.log4j.Logger;

@Mod(modid = ModConstants.MOD_ID, name = ModConstants.NAME, version = ModConstants.VERSION)
public final class ExampleMod {
    private static Logger logger;

    @Mod.EventHandler
    public void preInit(FMLPreInitializationEvent event) {
        logger = event.getModLog();
        ModNetwork.register();
    }

    public static Logger getLogger() {
        return logger;
    }
}
