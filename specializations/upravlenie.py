"""
specializations/upravlenie.py: Хэндлеры для Управленческая деятельность теста.
Production-ready с PDF, статистикой, автоудалением.
"""
import asyncio
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext

from library import (
    TestStates,
    Difficulty,
    CurrentTestState,
    load_questions_for_specialization,
    create_timer,
    get_difficulty_keyboard,
    show_question,
    handle_answer_toggle,
    handle_next_question,
    finish_test,
    get_main_keyboard,
    generate_certificate,
    stats_manager
)

logger = logging.getLogger(__name__)

upravlenie_router = Router(name="upravlenie")


@upravlenie_router.callback_query(F.data == "spec_upravlenie")
async def select_upravlenie(callback: CallbackQuery, state: FSMContext):
    """Выбор специализации Управленческая деятельность → запрос ФИО."""
    # Удаляем предыдущее сообщение (с логотипом или без)
    try:
        await callback.message.delete()
    except Exception:
        pass
    
    # Отправляем НОВОЕ сообщение
    await callback.message.answer(
        "💼 <b>Управленческая деятельность</b>\n\nВведите ваше ФИО:"
    )
    await state.set_state(TestStates.waiting_full_name)
    await state.update_data(specialization="upravlenie")
    await callback.answer()


@upravlenie_router.message(StateFilter(TestStates.waiting_full_name))
async def process_name(message: Message, state: FSMContext):
    """ФИО → должность."""
    await state.update_data(full_name=message.text.strip())
    await message.answer("Введите вашу должность:")
    await state.set_state(TestStates.waiting_position)


@upravlenie_router.message(StateFilter(TestStates.waiting_position))
async def process_position(message: Message, state: FSMContext):
    """Должность → отдел."""
    await state.update_data(position=message.text.strip())
    await message.answer("Введите ваше подразделение:")
    await state.set_state(TestStates.waiting_department)


@upravlenie_router.message(StateFilter(TestStates.waiting_department))
async def process_department(message: Message, state: FSMContext):
    """Отдел → выбор сложности."""
    await state.update_data(department=message.text.strip())
    await message.answer(
        "Выберите уровень сложности:",
        reply_markup=get_difficulty_keyboard()
    )
    await state.set_state(TestStates.waiting_difficulty)


@upravlenie_router.callback_query(
    F.data.startswith("diff_"),
    StateFilter(TestStates.waiting_difficulty)
)
async def select_difficulty(callback: CallbackQuery, state: FSMContext):
    """Сложность → загрузка вопросов → старт теста."""
    try:
        diff_name = callback.data.split("_", 1)[1]
        difficulty = Difficulty(diff_name)
        
        user_data = await state.get_data()
        specialization = user_data.get("specialization", "upravlenie")
        
        questions = load_questions_for_specialization(
            specialization,
            difficulty,
            callback.from_user.id
        )
        
        if not questions:
            await callback.message.edit_text(
                "❌ Не удалось загрузить вопросы. Попробуйте позже."
            )
            await state.clear()
            return
        
        test_state = CurrentTestState(
            questions=questions,
            specialization=specialization,
            difficulty=difficulty,
            full_name=user_data.get("full_name", ""),
            position=user_data.get("position", ""),
            department=user_data.get("department", "")
        )
        
        async def on_timeout():
            await finish_test(callback, state)
        
        timer = create_timer(difficulty, on_timeout)
        await timer.start()
        test_state.timer_task = timer
        
        await stats_manager.update_user_activity(callback.from_user.id)
        
        await state.update_data(test_state=test_state)
        await state.set_state(TestStates.answering_question)
        await show_question(callback, test_state, question_index=0)
        await callback.answer()
        
        logger.info(f"▶️ {callback.from_user.id} начал {specialization} ({difficulty.value})")
        
    except ValueError:
        await callback.answer("❌ Неверный уровень сложности")


@upravlenie_router.callback_query(
    F.data.startswith("ans_"),
    StateFilter(TestStates.answering_question)
)
async def answer_toggle(callback: CallbackQuery, state: FSMContext):
    """Toggle выбора ответа."""
    await handle_answer_toggle(callback, state)


@upravlenie_router.callback_query(
    F.data == "next",
    StateFilter(TestStates.answering_question)
)
async def next_question(callback: CallbackQuery, state: FSMContext):
    """Следующий вопрос."""
    await handle_next_question(callback, state)


@upravlenie_router.callback_query(F.data == "show_answers")
async def show_correct_answers(callback: CallbackQuery, state: FSMContext):
    """Показать правильные ответы (автоудаление через 60 сек)."""
    data = await state.get_data()
    test_state: CurrentTestState = data.get("test_state")
    
    if not test_state:
        await callback.answer("❌ Данные теста не найдены")
        return
    
    answers_text = "📋 <b>Правильные ответы:</b>\n\n"
    
    for i, question in enumerate(test_state.questions, 1):
        user_answer = test_state.answers_history.get(i - 1, set())
        correct = question.correct_answers
        is_correct = user_answer == correct
        emoji = "✅" if is_correct else "❌"
        correct_nums = ", ".join(str(n) for n in sorted(correct))
        answers_text += f"{emoji} <b>Вопрос {i}:</b> {correct_nums}\n"
    
    answers_text += "\n⏱ <i>Это сообщение будет удалено через 60 секунд</i>"
    
    msg = await callback.message.answer(answers_text)
    await callback.answer()
    
    async def delete_after_timeout():
        await asyncio.sleep(60)
        try:
            await msg.delete()
        except Exception as e:
            logger.warning(f"⚠️ Не удалось удалить: {e}")
    
    asyncio.create_task(delete_after_timeout())


@upravlenie_router.callback_query(F.data == "generate_cert")
async def generate_cert_handler(callback: CallbackQuery, state: FSMContext):
    """Генерация PDF сертификата."""
    data = await state.get_data()
    test_state: CurrentTestState = data.get("test_state")
    
    if not test_state:
        await callback.answer("❌ Данные теста не найдены")
        return
    
    await callback.answer("📄 Генерация сертификата...")
    
    try:
        pdf_buffer = await generate_certificate(test_state, callback.from_user.id)
        
        if not pdf_buffer:
            await callback.message.answer("❌ Ошибка генерации сертификата")
            return
        
        pdf_file = BufferedInputFile(
            pdf_buffer.read(),
            filename=f"certificate_{test_state.specialization}.pdf"
        )
        
        await callback.message.answer_document(
            pdf_file,
            caption=(
                f"🏆 <b>Ваш сертификат готов!</b>\n\n"
                f"Специализация: {test_state.specialization.upper()}\n"
                f"Оценка: {test_state.grade.upper()}\n"
                f"Результат: {test_state.percentage:.1f}%"
            )
        )
        
    except Exception as e:
        logger.error(f"❌ Ошибка генерации сертификата: {e}", exc_info=True)
        await callback.message.answer("❌ Ошибка при генерации")


@upravlenie_router.callback_query(F.data == "repeat_test")
async def repeat_test(callback: CallbackQuery, state: FSMContext):
    """Повторить тест."""
    await state.clear()
    await select_upravlenie(callback, state)


@upravlenie_router.callback_query(F.data == "my_stats")
async def show_stats_handler(callback: CallbackQuery):
    """Показать статистику."""
    try:
        stats = await stats_manager.get_user_stats(callback.from_user.id)
        
        if stats.get("total_tests", 0) == 0:
            await callback.message.answer(
                "📊 <b>Ваша статистика</b>\n\n"
                "У вас пока нет пройденных тестов.\n"
                "Начните тестирование прямо сейчас!"
            )
            await callback.answer()
            return
        
        stats_text = (
            f"📊 <b>Ваша статистика</b>\n\n"
            f"📝 Всего тестов: {stats['total_tests']}\n"
            f"📈 Средний балл: {stats['avg_percentage']}%\n"
            f"🏆 Лучший результат: {stats['best_result']}%\n"
            f"📉 Худший результат: {stats['worst_result']}%"
        )
        
        if stats.get('recent_tests'):
            stats_text += "\n\n<b>Последние тесты:</b>\n"
            for r in stats['recent_tests']:
                stats_text += (
                    f"• {r['specialization']} ({r['difficulty']}): "
                    f"{r['grade']} - {r['percentage']:.1f}%\n"
                )
        
        await callback.message.answer(stats_text)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"❌ Ошибка статистики: {e}", exc_info=True)
        await callback.answer("❌ Ошибка загрузки")


@upravlenie_router.callback_query(F.data == "main_menu")
async def back_to_main(callback: CallbackQuery, state: FSMContext):
    """Главное меню."""
    await state.clear()
    await callback.message.edit_text(
        "🧪 <b>ФССП Тест-бот</b>\n\nВыберите специализацию:",
        reply_markup=get_main_keyboard()
    )
    await callback.answer()


@upravlenie_router.callback_query(F.data == "help")
async def show_help(callback: CallbackQuery):
    """Помощь."""
    help_text = (
        "❓ <b>Помощь по боту</b>\n\n"
        "<b>Как пройти тест:</b>\n"
        "1️⃣ Выберите специализацию\n"
        "2️⃣ Введите данные (ФИО, должность, подразделение)\n"
        "3️⃣ Выберите уровень сложности\n"
        "4️⃣ Отвечайте на вопросы (1️⃣2️⃣3️⃣...)\n"
        "5️⃣ Нажмите ➡️ Далее\n"
        "6️⃣ Получите результат и сертификат\n\n"
        "<b>Команды:</b>\n"
        "/start - начать заново\n"
        "/stats - статистика\n"
        "/help - справка\n\n"
        "Удачи! 🍀"
    )
    await callback.message.edit_text(help_text, reply_markup=get_main_keyboard())
    await callback.answer()
