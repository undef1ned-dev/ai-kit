package com.example.examplemod.network;

import com.example.examplemod.tileentity.TileEntityGrinder;
import io.netty.buffer.ByteBuf;
import net.minecraft.client.Minecraft;
import net.minecraft.entity.player.EntityPlayerMP;
import net.minecraft.tileentity.TileEntity;
import net.minecraft.util.math.BlockPos;
import net.minecraftforge.fml.common.network.simpleimpl.IMessage;
import net.minecraftforge.fml.common.network.simpleimpl.IMessageHandler;
import net.minecraftforge.fml.common.network.simpleimpl.MessageContext;

public class SetModeMessage implements IMessage {
    public BlockPos pos;
    public int mode;

    public SetModeMessage() {
    }

    public SetModeMessage(BlockPos pos, int mode) {
        this.pos = pos;
        this.mode = mode;
    }

    @Override
    public void fromBytes(ByteBuf buf) {
        pos = BlockPos.fromLong(buf.readLong());
        mode = buf.readInt();
    }

    @Override
    public void toBytes(ByteBuf buf) {
        buf.writeLong(pos.toLong());
        buf.writeInt(mode);
    }

    public static class Handler implements IMessageHandler<SetModeMessage, IMessage> {
        @Override
        public IMessage onMessage(SetModeMessage message, MessageContext ctx) {
            EntityPlayerMP player = ctx.getServerHandler().player;
            TileEntity tile = player.world.getTileEntity(message.pos);
            if (tile instanceof TileEntityGrinder) {
                ((TileEntityGrinder) tile).setMode(TileEntityGrinder.GrinderMode.values()[message.mode]);
                Minecraft.getMinecraft().player.sendChatMessage("Grinder mode changed");
            }
            return null;
        }
    }
}
