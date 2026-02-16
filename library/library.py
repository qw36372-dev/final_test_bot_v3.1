"""
Основная логика теста: показ вопросов, обработка ответов, завершение.
Production-ready с правильной обработкой toggle и истории ответов.
"""
import logging
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from .models import CurrentTestState, Question
from .keyboards import get_test_keyboard, get_finish_keyboard
from .states import TestStates

logger = logging.getLogger(__name__)


async def show_question(
    callback: CallbackQuery | Message,
    test_state: CurrentTestState,
    question_index: int | None = None
):
    """
    Показать вопрос пользователю.
    Варианты ответов показываются в тексте сообщения, кнопки - только эмодзи.
    
    Args:
        callback: CallbackQuery или Message для отправки
        test_state: Состояние теста
        question_index: Индекс вопроса (если None, используется current_index)
    """
    if question_index is not None:
        test_state.current_index = question_index
    
    # Получаем текущий вопрос
    question = test_state.questions[test_state.current_index]
    
    # Загружаем ранее выбранные ответы (если есть)
    test_state.load_answer(test_state.current_index)
    
    # Формируем текст с вариантами ответов
    timer_text = test_state.timer_task.remaining_time() if test_state.timer_task else "∞"
    
    # Заголовок
    header = (
        f"⏰ Осталось: <b>{timer_text}</b>\n\n"
        f"📝 <b>Вопрос {test_state.current_index + 1}/{len(test_state.questions)}</b>"
    )
    
    # Вопрос
    question_text = f"\n\n{question.question}\n\n"
    
    # Варианты ответов с эмодзи
    options_text = "<b>Варианты ответов:</b>\n"
    for i, option in enumerate(question.options, start=1):
        emoji = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣"][i-1] if i <= 6 else f"{i}️⃣"
        # Отмечаем выбранные варианты
        mark = "✅ " if i in test_state.selected_answers else ""
        options_text += f"{mark}{emoji} {option}\n"
    
    full_text = header + question_text + options_text
    
    # Клавиатура - ТОЛЬКО эмодзи
    keyboard = get_test_keyboard(len(question.options), test_state.selected_answers)
    
    # Удаляем предыдущее сообщение с вопросом (если есть)
    if test_state.last_message_id:
        try:
            if isinstance(callback, CallbackQuery):
                await callback.bot.delete_message(
                    chat_id=callback.message.chat.id,
                    message_id=test_state.last_message_id
                )
        except Exception as e:
            logger.debug(f"Не удалось удалить предыдущее сообщение: {e}")
    
    # Отправляем НОВОЕ сообщение с вопросом
    if isinstance(callback, CallbackQuery):
        msg = await callback.message.answer(full_text, reply_markup=keyboard)
        test_state.last_message_id = msg.message_id  # Сохраняем ID
    else:
        msg = await callback.answer(full_text, reply_markup=keyboard)
        test_state.last_message_id = msg.message_id  # Сохраняем ID


async def handle_answer_toggle(
    callback: CallbackQuery,
    state: FSMContext
):
    """
    Обработка нажатия на вариант ответа (toggle).
    
    Args:
        callback: CallbackQuery с данными ans_{number}
        state: FSM context
    """
    try:
        # Извлекаем номер ответа из callback_data
        answer_num = int(callback.data.split("_")[1])
        
        # Получаем состояние теста
        data = await state.get_data()
        test_state: CurrentTestState = data.get("test_state")
        
        if not test_state:
            await callback.answer("❌ Ошибка: тест не найден")
            return
        
        # Toggle: добавляем или убираем ответ
        if answer_num in test_state.selected_answers:
            test_state.selected_answers.discard(answer_num)
            logger.debug(f"➖ Убран ответ {answer_num}")
        else:
            test_state.selected_answers.add(answer_num)
            logger.debug(f"➕ Добавлен ответ {answer_num}")
        
        # Обновляем ТЕКУЩЕЕ сообщение (только клавиатуру + текст с галочками)
        question = test_state.questions[test_state.current_index]
        timer_text = test_state.timer_task.remaining_time() if test_state.timer_task else "∞"
        
        header = (
            f"⏰ Осталось: <b>{timer_text}</b>\n\n"
            f"📝 <b>Вопрос {test_state.current_index + 1}/{len(test_state.questions)}</b>"
        )
        question_text = f"\n\n{question.question}\n\n"
        options_text = "<b>Варианты ответов:</b>\n"
        for i, option in enumerate(question.options, start=1):
            emoji = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣"][i-1] if i <= 6 else f"{i}️⃣"
            mark = "✅ " if i in test_state.selected_answers else ""
            options_text += f"{mark}{emoji} {option}\n"
        
        full_text = header + question_text + options_text
        keyboard = get_test_keyboard(len(question.options), test_state.selected_answers)
        
        try:
            await callback.message.edit_text(full_text, reply_markup=keyboard)
        except Exception as e:
            logger.warning(f"⚠️ Не удалось обновить: {e}")
        
        await callback.answer()
        
        # Сохраняем состояние
        await state.update_data(test_state=test_state)
        
    except (ValueError, IndexError, AttributeError) as e:
        logger.error(f"❌ Ошибка toggle ответа: {e}")
        await callback.answer("❌ Ошибка обработки ответа")


async def handle_next_question(
    callback: CallbackQuery,
    state: FSMContext
):
    """
    Обработка кнопки "Далее" - переход к следующему вопросу.
    
    Args:
        callback: CallbackQuery
        state: FSM context
    """
    try:
        # Получаем состояние теста
        data = await state.get_data()
        test_state: CurrentTestState = data.get("test_state")
        
        if not test_state:
            await callback.answer("❌ Ошибка: тест не найден")
            return
        
        # Сохраняем текущий ответ в историю
        test_state.save_answer(test_state.current_index)
        
        # Очищаем выбор для следующего вопроса
        test_state.selected_answers.clear()
        
        # Переходим к следующему вопросу
        test_state.current_index += 1
        
        # Проверяем, не закончились ли вопросы
        if test_state.current_index >= len(test_state.questions):
            await finish_test(callback, state)
            return
        
        # Показываем следующий вопрос
        await show_question(callback, test_state)
        
        # Сохраняем состояние
        await state.update_data(test_state=test_state)
        await callback.answer()
        
        logger.info(
            f"➡️ Пользователь {callback.from_user.id}: "
            f"вопрос {test_state.current_index + 1}/{len(test_state.questions)}"
        )
        
    except Exception as e:
        logger.error(f"❌ Ошибка перехода к следующему вопросу: {e}", exc_info=True)
        await callback.answer("❌ Ошибка перехода к следующему вопросу")


async def finish_test(
    callback: CallbackQuery,
    state: FSMContext
):
    """
    Завершение теста: подсчет результатов, сохранение в БД, отображение.
    
    Args:
        callback: CallbackQuery
        state: FSM context
    """
    try:
        # Получаем состояние теста
        data = await state.get_data()
        test_state: CurrentTestState = data.get("test_state")
        
        if not test_state:
            await callback.message.answer("❌ Ошибка: тест не найден")
            return
        
        # Останавливаем таймер
        if test_state.timer_task:
            test_state.timer_task.stop()
        
        # Подсчитываем результаты
        test_state.calculate_results()
        
        # Сохраняем результат в БД
        from .stats import stats_manager
        await stats_manager.save_result(callback.from_user.id, test_state)
        
        # Формируем сообщение с результатами
        grade_emoji = {
            "отлично": "🏆",
            "хорошо": "👍",
            "удовлетворительно": "👌",
            "неудовлетворительно": "❌"
        }
        
        emoji = grade_emoji.get(test_state.grade, "📊")
        
        result_text = (
            f"{emoji} <b>Тест завершён!</b>\n\n"
            f"👤 <b>ФИО:</b> {test_state.full_name}\n"
            f"💼 <b>Должность:</b> {test_state.position}\n"
            f"🏢 <b>Подразделение:</b> {test_state.department}\n"
            f"📚 <b>Специализация:</b> {test_state.specialization}\n"
            f"📊 <b>Уровень сложности:</b> {test_state.difficulty.value.capitalize()}\n\n"
            f"✅ <b>Оценка:</b> {test_state.grade.upper()}\n"
            f"📈 <b>Правильных ответов:</b> {test_state.correct_count} из {test_state.total_questions}\n"
            f"💯 <b>Процент:</b> {test_state.percentage:.1f}%\n"
            f"⏱ <b>Время:</b> {test_state.elapsed_time}"
        )
        
        # Отправляем результаты с клавиатурой
        keyboard = get_finish_keyboard()
        await callback.message.edit_text(result_text, reply_markup=keyboard)
        
        # Меняем состояние FSM
        await state.set_state(TestStates.showing_results)
        await state.update_data(test_state=test_state)
        
        logger.info(
            f"🏁 Пользователь {callback.from_user.id} завершил тест: "
            f"{test_state.percentage:.1f}% ({test_state.grade})"
        )
        
    except Exception as e:
        logger.error(f"❌ Ошибка завершения теста: {e}", exc_info=True)
        await callback.message.answer("❌ Ошибка при завершении теста")
