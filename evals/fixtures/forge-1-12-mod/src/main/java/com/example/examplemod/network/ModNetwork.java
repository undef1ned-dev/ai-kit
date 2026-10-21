package com.example.examplemod.network;

import com.example.examplemod.ModConstants;
import net.minecraftforge.fml.common.network.NetworkRegistry;
import net.minecraftforge.fml.common.network.simpleimpl.SimpleNetworkWrapper;
import net.minecraftforge.fml.relauncher.Side;

public final class ModNetwork {
    public static final SimpleNetworkWrapper CHANNEL = NetworkRegistry.INSTANCE.newSimpleChannel(ModConstants.MOD_ID);
    private static final int SET_MODE_ID = 0;

    private ModNetwork() {
    }

    public static void register() {
        CHANNEL.registerMessage(SetModeMessage.Handler.class, SetModeMessage.class, SET_MODE_ID, Side.SERVER);
    }
}
